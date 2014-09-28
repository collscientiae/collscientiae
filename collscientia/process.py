# coding: utf8
from __future__ import absolute_import
from logging import Logger
import markdown
import re
from .models import Code, Document
from .db import CollScientiaDB

knowl_id_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.]+$")


class IgnorePattern(markdown.inlinepatterns.Pattern):

    def handleMatch(self, m):
        return m.group(2)


class HashTagPattern(markdown.inlinepatterns.Pattern):

    def __init__(self, pattern, cp):
        self.cp = cp
        super(HashTagPattern, self).__init__(pattern)

    def handleMatch(self, m):
        el = markdown.util.etree.Element("a")
        ht = m.group(2).lower()
        self.cp.register_hashtag(ht)
        el.set('href', '../hashtag/{}.html'.format(ht))
        el.text = '#' + m.group(2)
        return el


class KnowlTagPatternWithTitle(markdown.inlinepatterns.Pattern):

    def handleMatch(self, m):
        tokens = m.group(2).split("|")
        kid = tokens[0].strip()
        kidsplit = kid.split("/")
        assert knowl_id_pattern.match(kidsplit[-1]), "Knowl ID '%s' invalid" % kidsplit[-1]
        assert 1 <= len(kidsplit) <= 2
        if len(kidsplit) == 2:
            from .models import namespace_pattern
            assert namespace_pattern.match(kidsplit[0])
        if len(tokens) > 1:
            t = ''.join(tokens[1:])
            return "{{ KNOWL('%s', title='%s') }}" % (kid, t.strip())
        return "{{ KNOWL('%s') }}" % kid


class ContentProcessor(object):

    """
    The one and only purpose of this Transformer class is to
    transform "content" to HTML.

    For now, it supports a healthy mix of Markdown (with some extras) and Jinja2-HTML.

    In the future, it might also be able to transform to LaTeX or PDF.
    """

    def __init__(self, logger, db):
        assert isinstance(db, CollScientiaDB)
        self.db = db
        assert isinstance(logger, Logger)
        self.logger = logger
        self.md = md = markdown.Markdown(
            extensions=['markdown.extensions.toc',
                        'markdown.extensions.extra',
                        'markdown.extensions.sane_lists',
                        'markdown.extensions.meta',
                        #'markdown.extensions.smarty',
                        'markdown.extensions.codehilite'])

        # Prevent $..$, $$..$$, \(..\), \[..\] blocks from being processed by Markdown
        md.inlinePatterns.add('mathjax$', IgnorePattern(r'(?<![\\\$])(\$[^\$].*?\$)'), '<escape')
        md.inlinePatterns.add('mathjax$$', IgnorePattern(r'(?<![\\])(\$\$.+?\$\$)'), '<escape')
        md.inlinePatterns.add('mathjax\\(', IgnorePattern(r'(\\\(.+?\\\))'), '<escape')
        md.inlinePatterns.add('mathjax\\[', IgnorePattern(r'(\\\[.+?\\\])'), '<escape')

        # double `` backtick `` for ASCIIMath
        # hope this doesn't confuse with <code> single backticks
        md.inlinePatterns.add('mathjax``', IgnorePattern(r'(?<![\\`])(``.+?``)'), '<escape')

        # Tell markdown to turn hashtags into search urls
        hashtag_keywords_rex = r'#([a-zA-Z][a-zA-Z0-9-_]{1,})\b'
        self.md.inlinePatterns.add('hashtag',
                                   HashTagPattern(hashtag_keywords_rex, self),
                                   '<escape')

        # Tells markdown to process "wikistyle" knowls with optional title
        # should cover {{ KID }} and {{ KID | title }}
        knowltagtitle_regex = r'knowl\[\[([^\]]+)\]\]'
        md.inlinePatterns.add('knowltagtitle', KnowlTagPatternWithTitle(knowltagtitle_regex), '<escape')

    def register_hashtag(self, hashtag):
        self.db.register_hashtag(hashtag, self.document)

    def convert(self, document, target="html"):
        """

        :type document: Document
        """
        self.document = document
        html = self.md.convert(document)
        meta = self.md.Meta.copy()
        assert isinstance(meta, dict)

        # only allowed keys
        allowed_keys = ["id", "authors", "copyright", "title",
                        "subtitle", "abstract", "date", "seealso"]
        for key in meta.keys():
            assert key in allowed_keys

        # no arrays for selected keys
        for key in allowed_keys:
            if key in ["authors", "seealso"]:
                continue
            if key in meta:
                # and join multilines
                meta[key] = '\n'.join(meta[key])

        return html, meta

