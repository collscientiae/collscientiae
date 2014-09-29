# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join, relpath, splitext
from os import makedirs, walk, link
from .models import Document
import codecs
import jinja2 as j2
import yaml

@j2.contextfilter
def filter_prefix(ctx, link):
    """
    Prepend level-times "../" to the given string.
    Used to go up in the directory hierarchy.
    Yes, one could also do absolute paths, but then it is harder to debug locally!
    """

    level = ctx.get("level", 0)
    if level == 0:
        return link
    path = ['..'] * level
    path.append(link)
    return '/'.join(path)

class OutputRenderer(object):

    def __init__(self, collscientia):
        self.log = collscientia.log
        self.db = collscientia.db
        self.src = collscientia.src
        self.theme = collscientia.theme
        self.targ = collscientia.targ

        self.tmpl_dir = join(self.theme, "src")
        j2loader = j2.FileSystemLoader(self.tmpl_dir)
        self.j2env = j2.Environment(loader=j2loader, undefined=j2.StrictUndefined)

        config = yaml.load(open(join(self.theme, "config.yaml")))
        self.j2env.globals.update(config)

        self.j2env.filters["prefix"] = filter_prefix

    def render_template(self, template_fn, target_fn, **data):
        tmpl = self.j2env.get_template(template_fn)
        html = tmpl.render(**data)
        with open(target_fn, "wb") as output:
            output.write(html.encode("utf-8"))
            output.write(b"\n")


    def copy_static_files(self):
        """
        This copies static files into the output file tree.
        """
        self.log.info("copying static files")
        for dir in ["static", "img"]:
            static_dir = join(self.tmpl_dir, dir)
            target_dir = join(self.targ, dir)
            makedirs(target_dir)
            for path, _, filenames in walk(static_dir):
                for fn in filenames:
                    if splitext(fn)[-1] in [".scss", ".sass"]:
                        continue
                    filepath = join(path, fn)
                    relative = relpath(path, static_dir)
                    targetpath = normpath(join(target_dir, relative, fn))
                    self.log.debug("link %s -> %s" % (join(relative, fn), targetpath))
                    link(filepath, targetpath)

    def output(self):
        self.log.info("rendering into %s" % self.targ)
        self.copy_static_files()
        self.output_index()
        self.output_documents()
        self.output_knowls()
        self.output_hashtags()

    def output_index(self):
        target_fn = join(self.targ, "index.html")
        self.render_template("index.html", target_fn,
                             modules=self.db.docs.keys())

    def output_knowls(self):
        for ns, docs in self.db.docs.iteritems():
            knowl_dir = join(self.targ, ns, "_knowl")
            assert not isdir(knowl_dir)
            makedirs(knowl_dir)
            for key, doc in docs.iteritems():
                out_fn = join(knowl_dir, '{}.{}'.format(doc.docid, "html"))

                # TODO: self.render_template(level = 2) !!!

                with codecs.open(out_fn, "w", "utf8") as out:
                    out.write("knowl: %s" % doc.docid)

    def output_documents(self):
        for ns, docs in self.db.docs.iteritems():
            doc_dir = join(self.targ, ns)
            makedirs(doc_dir)

            with codecs.open(join(doc_dir, "index.html"), "w", "utf8") as out:
                out.write("""<a href="../index.html">up</a> |
                <a href="_knowl/">knowls</a>
                <h1>{0}</h1>
                <br>
                <ul>""".format(ns))
                for key in docs.keys():
                    out.write("<li><a href='{0}.html'>{0}</a></li>".format(key))
                out.write("<ul>")

            for key, doc in docs.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(doc_dir, '{}.{}'.format(doc.docid, "html"))
                self.log.debug("  + %s" % out_fn)

                # TODO: self.render_template(level = 1) !!!

                with codecs.open(out_fn, "w", "utf8") as out:
                    out.write(u"""<a href="../index.html">up</a> |
                    <a href="index.html">index</a>
                    <br>
                    <h1>{0.title}</h1>
                    <div><i>Abstract:</i>{0.abstract}</div>
                    <h2>Content:</h2>
                    {0.output}
                    """.format(doc))

    def output_hashtags(self):
        hashtag_dir = join(self.targ, "hashtag")
        makedirs(hashtag_dir)
        hashtags = sorted(self.db.hashtags.iteritems(),
                          key=lambda _: _[0])

        with open(join(hashtag_dir, "index.html"), "w") as out:
            out.write("""<a href="../index.html">up</a>
            <h1>Hashtags</h1>""")
            out.write("<ul>")
            for h in hashtags:
                link = "<li><a href='{0}.html'>#{0}</a></li>\n".format(h[0])
                out.write(link)
            out.write("</ul>")

        for hashtag, docs in hashtags:
            out_fn = join(hashtag_dir, '{}.{}'.format(hashtag, "html"))

            # TODO: self.render_template(level = 1) !!!

            self.log.debug("  # %s" % out_fn)
            with open(out_fn, "w") as out:
                out.write("""<a href="../index.html">up</a> |
                            <a href="index.html">index</a>
                            <br>""")
                out.write("<ul>")
                for d in docs:
                    link = "<li><a href='../{0.namespace}/{0.docid}.html'>{0.docid}</a></li>" \
                        .format(d)
                    out.write(link)
                out.write("</ul>")
