# coding: utf8
from __future__ import absolute_import, unicode_literals
from logging import Logger
import markdown
import re
from .models import Document
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
        from markdown.util import etree
        a = etree.Element("a")
        ht = m.group(2).lower()
        self.cp.register_hashtag(ht)
        a.set('href', '../hashtag/{}.html'.format(ht))
        a.text = '#' + m.group(2)
        return a


class KnowlTagPatternWithTitle(markdown.inlinepatterns.Pattern):
    def __init__(self, pattern, cp):
        self.cp = cp
        super(KnowlTagPatternWithTitle, self).__init__(pattern)

    def handleMatch(self, m):
        from markdown.util import etree
        from .models import namespace_pattern
        tokens = m.group(2).split("|")
        kid = tokens[0].strip()
        kidsplit = kid.split("/")
        assert knowl_id_pattern.match(kidsplit[-1]), "Knowl ID '%s' invalid" % kidsplit[-1]
        assert 1 <= len(kidsplit) <= 2
        if len(kidsplit) == 2:
            target_ns = kidsplit[0]
        else:
            target_ns = self.cp.document.namespace
        target_ns = self.cp.cs.remap_module(self.cp.document.namespace, target_ns)
        assert namespace_pattern.match(target_ns)
        kid = target_ns + "/" + kidsplit[-1]
        self.cp.register_knowl(kid)
        a = etree.Element("a")
        a.set("knowl", kid)
        if len(tokens) > 1:
            t = ''.join(tokens[1:])
            a.text = t.strip()
        else:
            a.text = kidsplit[-1]
        return a


class CollScientiaCodeBlockProcessor(markdown.blockprocessors.CodeBlockProcessor):

    codeblock_pattern = re.compile(r"^([Pp]lot|[Ee]xample)::\s*$")

    def run(self, parent, blocks):
        # interceptor: only match in such a case, where sibling matches the
        # code_intro_pattern and remove it.

        sibling = self.lastChild(parent)
        codeblocks = []

        if sibling is not None and sibling.text is not None:
            if CollScientiaCodeBlockProcessor.codeblock_pattern.match(sibling.text):
                while True:
                    i = len(codeblocks)
                    if markdown.blockprocessors.CodeBlockProcessor.test(self, parent, blocks[i]):
                        code, dedented = self.detab(blocks[i])
                        if dedented != '':
                            raise ValueError(
                                "There is dedented text below a codeblock.\n'%s'" % dedented)
                        codeblocks.append(code)
                    else:
                        break

        parent.remove(sibling)

        return markdown.blockprocessors.CodeBlockProcessor.run(self, parent, blocks)


class ContentProcessor(object):

    """
    The one and only purpose of this Transformer class is to
    transform "content" to HTML.

    For now, it supports a healthy mix of Markdown (with some extras) and Jinja2-HTML.

    In the future, it might also be able to transform to LaTeX or PDF.
    """

    def __init__(self, cs):
        self.cs = cs
        db = cs.db
        logger = cs.log
        assert isinstance(db, CollScientiaDB)
        self.db = db
        self.document = None
        assert isinstance(logger, Logger)
        self.logger = logger
        self.j2env = cs.j2env
        self.md = self.init_md()

    def init_md(self):
        md = markdown.Markdown(
            extensions=['markdown.extensions.toc',
                        'markdown.extensions.extra',
                        'markdown.extensions.sane_lists',
                        'markdown.extensions.meta',
                        #'markdown.extensions.smarty',
                        #'markdown.extensions.codehilite'
                        ])

        # Prevent $..$, $$..$$, \(..\), \[..\] blocks from being processed by Markdown
        md.inlinePatterns.add('mathjax$', IgnorePattern(r'(?<![\\\$])(\$[^\$].*?\$)'), '<escape')
        md.inlinePatterns.add('mathjax$$', IgnorePattern(r'(?<![\\])(\$\$.+?\$\$)'), '<escape')
        md.inlinePatterns.add('mathjax\\(', IgnorePattern(r'(\\\(.+?\\\))'), '<escape')
        md.inlinePatterns.add('mathjax\\[', IgnorePattern(r'(\\\[.+?\\\])'), '<escape')

        # double `` backtick `` for ASCIIMath
        # hope this doesn't confuse with <code> single backticks
        md.inlinePatterns.add('mathjax``',
                              IgnorePattern(r'(?<![\\`])(``.+?``)'),
                              '<escape')

        # Tell markdown to turn hashtags into search urls
        hashtag_keywords_rex = r'#([a-zA-Z][a-zA-Z0-9-_]{1,})\b'
        md.inlinePatterns.add('hashtag',
                                   HashTagPattern(hashtag_keywords_rex, self),
                                   '<escape')

        # Tells markdown to process "wikistyle" knowls with optional title
        knowltagtitle_regex = r'knowl\[\[([^\]]+)\]\]'
        md.inlinePatterns.add('knowltagtitle',
                              KnowlTagPatternWithTitle(knowltagtitle_regex, self),
                              '<escape')

        # codeblocks with plot:: or example:: prefixes
        md.parser.blockprocessors["code"] = CollScientiaCodeBlockProcessor(md.parser)
        return md

    def register_hashtag(self, hashtag):
        self.db.register_hashtag(hashtag, self.document)

    def register_knowl(self, knowl_id):
        self.db.register_knowl(knowl_id)

    def get_metadata(self):
        meta = self.md.Meta.copy()
        assert isinstance(meta, dict)

        # only allowed keys
        allowed_keys = ["authors", "copyright", "title", "type",
                        "subtitle", "abstract", "date", "seealso"]

        for key in meta:
            assert key in allowed_keys, "{} not allowed".format(key)

        if "type" in meta:
            mt = meta["type"]
            assert len(mt) == 1
            mt = mt[0]
            assert mt in Document.allowed_types,\
                "{} not an allowed type".format(mt)
            meta["type"] = mt
        else:
            meta["type"] = Document.allowed_types[0]

        # no arrays for selected keys
        for key in allowed_keys:
            if key in ["authors", "seealso", "type"]:
                continue
            if key in meta:
                # and join multilines
                meta[key] = '\n'.join(meta[key])

        return meta

    def convert(self, document, target="html"):
        """

        :type document: Document
        """
        assert isinstance(document, Document)
        self.document = document
        html = self.md.convert(document.md_raw)
        html = """{% include "macros.html" %}\n""" + html
        html = self.j2env.from_string(html).render()
        print html
        meta = self.get_metadata()

        return html, meta
