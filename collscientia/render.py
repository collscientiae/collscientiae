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
        if config is not None:
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
        ignored_static_files = [".scss", ".sass"]
        for dir in ["static", "img"]:
            static_dir = join(self.tmpl_dir, dir)
            target_dir = join(self.targ, dir)
            makedirs(target_dir)
            for path, _, filenames in walk(static_dir):
                for fn in filenames:
                    if fn.startswith("_") or splitext(fn)[-1] in ignored_static_files:
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
        index_fn = join(self.targ, "index.html")
        modules = sorted(self.db.modules.values(),
                         key=lambda _: _.name)
        self.render_template("index_modules.html",
                             index_fn,
                             modules=modules)

    def output_knowls(self):
        for ns, modules in self.db.modules.iteritems():
            knowl_dir = join(self.targ, ns, "_knowl")
            assert not isdir(knowl_dir)
            makedirs(knowl_dir)
            for key, doc in modules.iteritems():
                out_fn = join(knowl_dir, '{}.{}'.format(doc.docid, "html"))

                # TODO: self.render_template(level = 2) !!!

                with codecs.open(out_fn, "w", "utf8") as out:
                    out.write("knowl: %s" % doc.docid)

    def output_documents(self):
        for ns, module in self.db.modules.iteritems():
            doc_dir = join(self.targ, ns)
            makedirs(doc_dir)

            doc_index = join(doc_dir, "index.html")
            links = [(_, _ + ".html") for _ in module.keys()]
            links.insert(0, ("Knowls", "_knowl/index.html"))

            self.render_template("index.html",
                                 doc_index,
                                 title=module.name,
                                 level=1,
                                 links=links)

            for key, doc in module.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(doc_dir, '{}.{}'.format(doc.docid, "html"))
                self.log.debug("  + %s" % out_fn)
                self.render_template("document.html",
                                     out_fn,
                                     title=doc.title,
                                     doc=doc,
                                     level=1)

    def output_hashtags(self):
        hashtag_dir = join(self.targ, "hashtag")
        makedirs(hashtag_dir)
        hashtags = sorted(self.db.hashtags.iteritems(),
                          key=lambda _: _[0])

        hashtag_index = join(hashtag_dir, "index.html")
        links = [("#" + _[0], _[0] + ".html") for _ in hashtags]
        self.render_template("index.html",
                             hashtag_index,
                             title="Hashtag Index",
                             level=1,
                             links=links)

        for hashtag, docs in hashtags:
            out_fn = join(hashtag_dir, hashtag + ".html")

            self.log.debug("  # " + out_fn)

            links = [('{0.docid}'.format(d),
                      '../{0.namespace}/{0.docid}.html'.format(d)) for d in docs]
            self.render_template("index.html",
                                 out_fn,
                                 title="Hashtag #" + hashtag,
                                 level=1,
                                 links=links)
