# coding: utf8

import markdown
import jinja2


class IgnorePattern(markdown.inlinepatterns.Pattern):

    def handleMatch(self, m):
        return m.group(2)


class HashTagPattern(markdown.inlinepatterns.Pattern):

    def handleMatch(self, m):
        el = markdown.util.etree.Element("a")
        el.set('href', 'hashtag/' + m.group(2))
        el.text = '#' + m.group(2)
        return el


class Processor(object):

    """
    The one and only purpose of this Transformer class is to
    transform "content" to HTML.

    For now, it supports a healthy mix of Markdown (with some extras) and Jinja2-HTML.

    In the future, it might also be able to transform to LaTeX or PDF.
    """

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=['markdown.extensions.toc',
                        'markdown.extensions.extra',
                        'markdown.extensions.sane_lists',
                        #'markdown.extensions.smarty',
                        'markdown.extensions.codehilite'])

        # Prevent $..$, $$..$$, \(..\), \[..\] blocks from being processed by Markdown
        self.md.inlinePatterns.add('mathjax$', IgnorePattern(r'(?<![\\\$])(\$[^\$].*?\$)'), '<escape')
        self.md.inlinePatterns.add('mathjax$$', IgnorePattern(r'(?<![\\])(\$\$.+?\$\$)'), '<escape')
        self.md.inlinePatterns.add('mathjax\\(', IgnorePattern(r'(\\\(.+?\\\))'), '<escape')
        self.md.inlinePatterns.add('mathjax\\[', IgnorePattern(r'(\\\[.+?\\\])'), '<escape')
        # double `` backtick `` for ASCIIMath -- hope this doesn't confuse with <code> single backticks
        self.md.inlinePatterns.add('mathjax``', IgnorePattern(r'(?<![\\`])(``.+?``)'), '<escape')

        # Tell markdown to turn hashtags into search urls
        hashtag_keywords_rex = r'#([a-zA-Z][a-zA-Z0-9-_]{1,})\b'
        self.md.inlinePatterns.add('hashtag', HashTagPattern(hashtag_keywords_rex), '<escape')

    def process(self, content, target="html"):
        return getattr(self, "process_%s" % target)(content)

    def process_html(self, content):
        return self.md.convert(content)
