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
        self.output_main_index()
        self.output_documents()
        self.output_document_indices()
        self.output_hashtags()

    def output_main_index(self):
        index_fn = join(self.cs.targ, "index.html")

        modules = [self.cs.db.modules[_] for _ in self.cs.config["modules"]]
        self.render_template("index_modules.html",
                             index_fn,
                             modules=modules)

    def render_document_index(self, ns, doc_id, children, doc_idx_fn=None):
        # TODO clean this mess up, it's used 2x!
        if doc_idx_fn is None:
            doc_idx_fn = join(self.cs.targ, ns, doc_id + ".html")
        links = []
        for key, node in children.iteritems():
            type = "dir" if len(node) > 0 else "file"
            if doc_id is None:
                href = '.'.join((key, "html"))
            else:
                href = '.'.join((doc_id, key, "html"))
            links.append((key.title(), href, type))
        bc = Document.mk_breadcrum(doc_id) if doc_id else []
        self.render_template("index.html",
                             doc_idx_fn,
                             namespace=ns,
                             level=1,
                             title=doc_id,
                             breadcrum=bc,
                             links=links)

    def output_document_indices(self):

        def walk(m, node, parents, depth=0):
            assert isinstance(m, DocumentationModule)
            # print "  " * depth, "+", key, "INDEX" if len(node) > 0 else "LEAF"
            if len(node) > 0:
                doc_id = ".".join(parents)
                if doc_id not in m:
                    self.render_document_index(m.namespace, doc_id, node)

            for key, node in node.iteritems():
                p = parents[:]
                p.append(key)
                walk(m, node, p, depth=depth + 1)

        for m in self.cs.db.modules.values():
            assert isinstance(m, DocumentationModule)
            for key, section in m.tree.iteritems():
                walk(m, section, [key])

    def output_documents(self):
        self.log.info("processing document templates")
        for ns, module in self.cs.db.modules.iteritems():
            assert isinstance(module, DocumentationModule)
            doc_dir = join(self.cs.targ, ns)
            makedirs(doc_dir)

            doc_index = join(doc_dir, "index.html")
            self.render_document_index(module.namespace, None, module.tree, doc_index)

            for key, doc in module.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(doc_dir, doc.docid + ".html")
                backlinks = self.cs.db.backlinks[(module.namespace, key)]
                self.log.debug("  + %s" % out_fn)
                seealso = [module[_] for _ in doc.seealso]
                self.render_template("document.html",
                                     out_fn,
                                     namespace=ns,
                                     breadcrum=doc.breadcrum(),
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
        links = [("#" + _[0], _[0] + ".html", "hashtag") for _ in hashtags]
        bc = [("#", "index")]
        self.render_template("index.html",
                             hashtag_index,
                             title="Hashtag Index",
                             breadcrum=bc,
                             level=1,
                             links=links)

        for hashtag, docs in hashtags:
            out_fn = join(hashtag_dir, hashtag + ".html")
            self.log.debug("  # " + out_fn)
            bc2 = bc + [(hashtag, hashtag)]
            links = [('{0.docid}'.format(d),
                      '../{0.namespace}/{0.docid}.html'.format(d),
                      'file') for d in docs]
            self.render_template("index.html",
                                 out_fn,
                                 title="Hashtag #" + hashtag,
                                 breadcrum=bc2,
                                 level=1,
                                 links=links)
