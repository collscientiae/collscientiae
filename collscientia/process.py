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


class KnowlTagPatternWithTitle(markdown.inlinepatterns.Pattern):

    def handleMatch(self, m):
        tokens = m.group(2).split("|")
        kid = tokens[0].strip()
        if len(tokens) > 1:
            t = ''.join(tokens[1:])
            return "{{ KNOWL('%s', title='%s') }}" % (kid, t.strip())
        return "{{ KNOWL('%s') }}" % kid


class Processor(object):

    """
    The one and only purpose of this Transformer class is to
    transform "content" to HTML.

    For now, it supports a healthy mix of Markdown (with some extras) and Jinja2-HTML.

    In the future, it might also be able to transform to LaTeX or PDF.
    """

    def __init__(self):
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
        self.md.inlinePatterns.add('hashtag', HashTagPattern(hashtag_keywords_rex), '<escape')

        # Tells markdown to process "wikistyle" knowls with optional title
        # should cover {{ KID }} and {{ KID | title }}
        knowltagtitle_regex = r'knowl::([^:]+):'
        md.inlinePatterns.add('knowltagtitle', KnowlTagPatternWithTitle(knowltagtitle_regex), '<escape')

    def process(self, content, target="html"):
        return getattr(self, "process_%s" % target)(content)

    def process_html(self, content):
        return self.md.convert(content)
