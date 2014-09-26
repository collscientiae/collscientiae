# coding: utf8
from __future__ import absolute_import
from logging import Logger
import markdown
import jinja2
import re
from .models import Code
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
        ht = m.group(2)
        self.cp.register_hashtag(ht)
        el.set('href', '../hashtag/' + ht)
        el.text = '#' + m.group(2)
        return el


class KnowlTagPatternWithTitle(markdown.inlinepatterns.Pattern):

    def handleMatch(self, m):
        tokens = m.group(2).split("|")
        kid = tokens[0].strip()
        kidsplit = kid.split("::")
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
        self.db.register_hashtag(hashtag, self.doc_id)

    def process(self, document, target="html"):
        content = document.content
        self.doc_id = document.id
        return getattr(self, "process_%s" % target)(content)

    def process_html(self, content):
        output = []
        for part in content:
            if isinstance(part, Code):
                c = part.to_html()
                output.append(c)
            else:
                output.append(self.md.convert(part))
        return "\n".join(output)
