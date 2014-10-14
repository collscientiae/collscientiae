# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join, relpath, splitext
from os import makedirs, walk, link
from collscientiae.models import DocumentationModule
from .models import Document
import codecs


class OutputRenderer(object):

    def __init__(self, collscientiae):
        self.log = collscientiae.log
        self.cs = collscientiae

    def render_template(self, template_fn, target_fn, **data):
        tmpl = self.cs.j2env.get_template(template_fn)
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
            static_dir = join(self.cs.tmpl_dir, dir)
            target_dir = join(self.cs.targ, dir)
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
        self.log.info("rendering into %s" % self.cs.targ)
        self.copy_static_files()
        self.output_index()
        self.output_documents()
        self.output_hashtags()

    def output_index(self):
        index_fn = join(self.cs.targ, "index.html")

        modules = [self.cs.db.modules[_] for _ in self.cs.config["modules"]]
        self.render_template("index_modules.html",
                             index_fn,
                             modules=modules)

    def output_documents(self):
        self.log.info("processing document templates")
        for ns, module in self.cs.db.modules.iteritems():
            assert isinstance(module, DocumentationModule)
            doc_dir = join(self.cs.targ, ns)
            makedirs(doc_dir)

            doc_index = join(doc_dir, "index.html")
            links = [(_, _ + ".html") for _ in module.keys()]

            self.render_template("index.html",
                                 doc_index,
                                 title=module.name,
                                 level=1,
                                 links=links)

            for key, doc in module.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(doc_dir, '{}.{}'.format(doc.docid, "html"))
                backlinks = self.cs.db.backlinks[(module.namespace, key)]
                self.log.debug("  + %s" % out_fn)
                seealso = [module[_] for _ in doc.seealso]
                self.render_template("document.html",
                                     out_fn,
                                     title=doc.title,
                                     doc=doc,
                                     seealso=seealso,
                                     backlinks=backlinks,
                                     level=1)

    def output_hashtags(self):
        self.log.info("  ... and hashtags")
        hashtag_dir = join(self.cs.targ, "hashtag")
        makedirs(hashtag_dir)
        hashtags = sorted(self.cs.db.hashtags.iteritems(),
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