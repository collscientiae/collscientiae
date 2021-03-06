# coding: utf8
from __future__ import absolute_import, unicode_literals
import hashlib
from logging import Logger
import markdown
import re
from .models import Document
from .db import CollScientiaeDB

document_id_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.]+$")
a_href_pattern = re.compile(r"<(a|A)[^>]+?href=")


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
        self.cp.db.register_hashtag(ht, self.cp.document)
        a.set('href', '../hashtag/{}.html'.format(ht))
        idx = m.lastindex - 1
        a.text = '#' + m.group(idx)
        return a


class LinkedDocument(markdown.inlinepatterns.Pattern):

    """
    parent class for Include, Link and Knowl Patterns
    """

    def __init__(self, pattern, cp):
        self.cp = cp
        assert isinstance(cp, ContentProcessor)
        self.doc_id = None
        self.label = None
        self.limit = None
        self.tokens = None
        self.target_ns = None
        super(LinkedDocument, self).__init__(pattern)

    def handleMatch(self, m):
        from .models import namespace_pattern

        self.tokens = m.group(2).split("|")
        raw_id = self.tokens[0].strip()
        id_split = raw_id.split("/")
        doc_id_tokens = id_split[-1].split()
        # reset label and limit and analyze the ID in detail
        self.label = None
        self.limit = None
        if len(doc_id_tokens) == 1:
            self.doc_id = doc_id_tokens[0]
        elif len(doc_id_tokens) == 2:
            self.doc_id, self.label = doc_id_tokens
        elif len(doc_id_tokens) == 3:
            self.doc_id, self.label, self.limit = doc_id_tokens
        else:
            raise ValueError("Include ID '%s' is invalid" % raw_id)

        assert 1 <= len(id_split) <= 2
        if len(id_split) == 2:
            self.target_ns = id_split[0]
        else:
            self.target_ns = self.cp.document.namespace
        self.target_ns = self.cp.cs.remap_module(self.cp.document.namespace, self.target_ns)

        assert document_id_pattern.match(self.doc_id), "Document ID '%s' invalid" % self.doc_id
        assert namespace_pattern.match(self.target_ns)

    def get_link(self):
        return self.target_ns + "/" + self.doc_id

    def set_element_attributes(self, element):

        if self.label:
            element.set("label", self.label)

        if self.limit:
            element.set("limit", self.limit)

        if len(self.tokens) > 1:
            t = ''.join(self.tokens[1:])
            element.text = t.strip()
        else:
            element.text = self.doc_id.split(".")[-1]


class IncludePattern(LinkedDocument):

    def handleMatch(self, m):
        LinkedDocument.handleMatch(self, m)
        from markdown.util import etree
        link = self.get_link()
        div = etree.Element("div")
        div.set("include", link)
        div.set("class", "include")
        self.set_element_attributes(div)
        return div


class LinkPattern(LinkedDocument):

    def handleMatch(self, m):
        LinkedDocument.handleMatch(self, m)
        from markdown.util import etree

        link = self.get_link()
        self.cp.db.register_link(self.target_ns, self.doc_id, self.cp.document)

        a = etree.Element("a")
        a.set("href", "../%s.html" % link)
        self.set_element_attributes(a)
        return a


class KnowlPattern(LinkedDocument):

    def handleMatch(self, m):
        LinkedDocument.handleMatch(self, m)
        from markdown.util import etree

        link = self.get_link()
        self.cp.db.register_knowl(self.target_ns, self.doc_id, self.cp.document)

        a = etree.Element("a")
        a.set("knowl", link)
        self.set_element_attributes(a)

        return a


class CollScientiaCodeBlockProcessor(markdown.blockprocessors.CodeBlockProcessor):

    codeblock_pattern = re.compile(r"^(plot|example|python|sage|r)::\s*(.*)$", re.IGNORECASE)

    def __init__(self, parser, cp):
        self.cp = cp
        self.log = cp.log
        self.cell_id_counter = 0
        markdown.blockprocessors.CodeBlockProcessor.__init__(self, parser)

    def run(self, parent, blocks):
        from markdown.util import etree, AtomicString

        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        theRest = ''
        if sibling and sibling.tag == 'div' and len(sibling) \
                and sibling[0].tag == 'code':
            # The previous block was a code block. As blank lines do not start
            # new code blocks, append this block to the previous, adding back
            # linebreaks removed from the split into a list.
            code = sibling[0]
            block, theRest = self.detab(block)
            code.text = AtomicString('%s\n%s\n' % (code.text, block.rstrip()))
        else:
            # This is a new codeblock. Create the elements and insert text.
            cell_id = "sagecell-%s" % self.cell_id_counter
            self.cell_id_counter += 1

            outer = etree.SubElement(parent, 'div')
            inner = etree.SubElement(outer, 'code')

            m = CollScientiaCodeBlockProcessor.codeblock_pattern.match(sibling.text)
            if m is not None:
                mode, args = m.groups()
                if mode == "plot":
                    self.log.warning("codeblock mode 'plot' not yet implemented")
                elif mode in ["sage", "python", "r"]:
                    # outer.tag = "code"
                    outer.set("mode", mode)
                    outer.set("id", cell_id)

                    inner.set("class", "language-" + mode)
                    # inner.tag = "pre"
                    inner.set("type", "text/x-sage")

                parent.remove(sibling)

            else:  # no preceding codeblock description, we assume python
                #outer.set("mode", "default")
                inner.set("class", "language-python")

            outer.set("class", "sagecell_init")

            block, theRest = self.detab(block)
            inner.text = AtomicString('%s\n' % block.rstrip())
        if theRest:
            # This block contained unindented line(s) after the first indented line.
            # Insert these lines as the first block of the master blocks list for future processing.
            blocks.insert(0, theRest)

    # def run(self, parent, blocks):
    # interceptor: only match in such a case, where sibling matches the
    # code_intro_pattern and remove it.
    #
    #     sibling = self.lastChild(parent)
    #     codeblocks = []
    #
    #     if sibling is not None and sibling.text is not None:
    #         if CollScientiaCodeBlockProcessor.codeblock_pattern.match(sibling.text):
    #             while True:
    #                 i = len(codeblocks)
    #                 if markdown.blockprocessors.CodeBlockProcessor.test(self, parent, blocks[i]):
    #                     code, dedented = self.detab(blocks[i])
    #                     if dedented != '':
    #                         raise ValueError(
    #                             "There is dedented text below a codeblock.\n'%s'" % dedented)
    #                     codeblocks.append(code)
    #                 else:
    #                     break
    #
    #     parent.remove(sibling)
    #
    #     return markdown.blockprocessors.CodeBlockProcessor.run(self, parent, blocks)


class ContentProcessor(object):

    """
    The one and only purpose of this Transformer class is to
    transform "content" to HTML.

    For now, it supports a healthy mix of Markdown (with some extras) and Jinja2-HTML.

    In the future, it might also be able to transform to LaTeX or PDF.
    """

    allowed_keys = ["authors", "copyright", "title", "type", "tags", "group",
                    "subtitle", "abstract", "date", "seealso", "sort"]

    required_keys = ["title"]

    def __init__(self, cs):
        self.cs = cs
        db = cs.db
        log = cs.log
        self.doc_root_hash = hashlib.sha1()
        # TODO update with documentation version and so on
        # self.doc_root_hash.update()
        assert isinstance(db, CollScientiaeDB)
        self.db = db
        self.document = None
        assert isinstance(log, Logger)
        self.log = log
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

        add = md.inlinePatterns.add

        # Prevent $..$, $$..$$, \(..\), \[..\] blocks from being processed by Markdown
        add('mathjax$', IgnorePattern(r'(?<![\\\$])(\$[^\$].*?\$)'), '<escape')
        add('mathjax$$', IgnorePattern(r'(?<![\\])(\$\$.+?\$\$)'), '<escape')
        add('mathjax\\(', IgnorePattern(r'(\\\(.+?\\\))'), '<escape')
        add('mathjax\\[', IgnorePattern(r'(\\\[.+?\\\])'), '<escape')

        # double '' for ASCIIMath (double backtick `` is <code>)
        add('mathjax``', IgnorePattern(r'(?<![\\`])(``.+?``)'), '<escape')

        # Tell markdown to turn hashtags into search urls
        hashtag_keywords_rex = r'#([a-zA-Z][a-zA-Z0-9-_]{1,})\b'
        add('hashtag', HashTagPattern(hashtag_keywords_rex, self), '<escape')

        hashtag_keywords_rex2 = r'#\[([a-zA-Z][a-zA-Z0-9-_]{1,})\s+([^\]]+)\]'
        add('hashtag2', HashTagPattern(hashtag_keywords_rex2, self), '<escape')

        # Tells markdown to process "wikistyle" links with optional title
        link_regex = r'link\[([^\]]+)\]'
        add('linktag', LinkPattern(link_regex, self), '<escape')

        # Tells markdown to process "wikistyle" knowosl with optional title
        knowl_regex = r'knowl\[([^\]]+)\]'
        add('knowltag', KnowlPattern(knowl_regex, self), '<escape')

        include_pattern = r'include\[([^\]]+)\]'
        add('includes', IncludePattern(include_pattern, self), '<escape')

        # codeblocks with plot:: or example:: prefixes
        md.parser.blockprocessors["code"] = CollScientiaCodeBlockProcessor(md.parser, self)
        return md

    def get_metadata(self):
        meta = self.md.Meta.copy()
        assert isinstance(meta, dict)

        # only allowed keys
        for key in meta:
            assert key in ContentProcessor.allowed_keys, \
                "{} not allowed".format(key)

        # required keys
        for key in ContentProcessor.required_keys:
            assert key in meta, "Meta Key {} not set for {}".format(key, self.document.docid)

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
        for key in ContentProcessor.allowed_keys:
            if key in meta:
                if key == "type":
                    continue
                elif key in ["authors", "seealso"]:
                    # filter empty ones
                    meta[key] = filter(lambda x: len(x) > 0, meta[key])
                else:
                    # and join multilines
                    meta[key] = '\n'.join(meta[key])

        # fixup seealso
        if "seealso" in meta:
            for sa in meta["seealso"]:
                if len(sa) == 0:
                    meta["seealso"].remove(sa)
                else:
                    assert document_id_pattern.match(sa), "ID '%s' not valid" % sa
        else:
            meta["seealso"] = []

        return meta

    def get_root_hash(self):
        rh = self.doc_root_hash.hexdigest()
        self.log.info("root hash: %s" % rh)
        return rh

    def convert(self, document, target="html"):
        """

        :type document: Document
        """
        assert isinstance(document, Document)
        self.document = document
        html = self.md.convert(document.md_raw)
        html = '\n'.join(
            ["""{% include "macros.html" %}""", html])
        try:
            html = self.j2env.from_string(html).render(namespace=document.namespace)
        except Exception as e:
            print(html)
            raise e
        meta = self.get_metadata()

        self.doc_root_hash.update(html.encode("utf8"))
        meta_frozen = [(k, tuple(v) if isinstance(v, list) else v)
                       for k, v in meta.items()]
        self.doc_root_hash.update(str(frozenset(meta_frozen)).encode("utf8"))

        return html, meta
