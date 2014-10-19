# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join, relpath, splitext, exists
from os import makedirs, walk, link
from collscientiae.models import DocumentationModule, Index
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

    def render_index(self, index, directory, fn, namespace=None, breadcrum=None, level=1):
        assert isinstance(index, Index)
        if not exists(directory):
            makedirs(directory)
        index_fn = join(directory, fn + ".html")
        self.render_template("index.html",
                             index_fn,
                             title=index.title,
                             namespace=namespace,
                             breadcrum=breadcrum,
                             level=level,
                             index=index)

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

    def render_document_index(self, module, doc_id, children):
        # TODO clean this mess up, it's used 2x!
        assert isinstance(module, DocumentationModule)
        ns = module.namespace
        doc_dir = join(self.cs.targ, ns)
        idx = Index(module.namespace)
        for key, node in children.iteritems():
            type = "dir" if len(node) > 0 else "file"
            if doc_id is None:
                href = key
            else:
                href = doc_id + "." + key
            if type == "file":
                doc = module[href]
                descr = doc.subtitle
                title = doc.title
            else:
                descr = None
                title = key.title()
            idx += Index.Entry(title, href, type=type, description=descr)

        bc = []
        if doc_id is None:
            fn = "index"
        else:
            fn = doc_id
            bc = Document.mk_breadcrum(doc_id)
            idx.title = " - ".join(_[0].title() for _ in reversed(bc))

        self.render_index(idx, doc_dir, fn=fn, namespace=ns, breadcrum=bc)

    def output_document_indices(self):
        self.log.info("writing document index files")

        def walk(m, node, parents, depth=0):
            assert isinstance(m, DocumentationModule)
            # print "  " * depth, "+", key, "INDEX" if len(node) > 0 else "LEAF"
            if len(parents) > 0:
                doc_id = ".".join(parents)
                if doc_id not in m:
                    self.render_document_index(m, doc_id, node)

            for key, node in node.iteritems():
                p = parents[:]
                p.append(key)
                walk(m, node, p, depth=depth + 1)

        for ns, module in self.cs.db.modules.iteritems():
            assert isinstance(module, DocumentationModule)
            self.render_document_index(module, None, module.tree)
            walk(module, module.tree, [])
            # for key, section in m.tree.iteritems():
            #    walk(m, section, [key])

    def output_documents(self):
        self.log.info("writing document templates")
        for ns, module in self.cs.db.modules.iteritems():
            assert isinstance(module, DocumentationModule)
            doc_dir = join(self.cs.targ, ns)
            makedirs(doc_dir)

            for key, doc in module.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(doc_dir, doc.docid + ".html")
                backlinks = self.cs.db.backlinks[(module.namespace, key)]
                self.log.debug("  + %s" % out_fn)
                seealso = [module[_] for _ in doc.seealso]
                bc = doc.breadcrum()
                title = " - ".join(_[0].title() for _ in reversed(bc))
                title = title + " - " + ns.title()
                self.render_template("document.html",
                                     out_fn,
                                     namespace=ns,
                                     breadcrum=bc,
                                     title=title,
                                     doc=doc,
                                     seealso=seealso,
                                     backlinks=backlinks,
                                     level=1)

    def output_hashtags(self):
        self.log.info("  ... and hashtags")
        hashtag_dir = join(self.cs.targ, "hashtag")
        hashtags = sorted(self.cs.db.hashtags.iteritems(),
                          key=lambda _: _[0])

        idx = Index("Hashtag Index")
        for ht in hashtags:
            idx += Index.Entry(ht[0], ht[0], type="hashtag")

        bc = [("#", "index")]
        self.render_index(idx, hashtag_dir, fn="index", breadcrum=bc)

        for hashtag, docs in hashtags:
            #out_fn = join(hashtag_dir, hashtag + ".html")
            self.log.debug("  # " + hashtag)
            bc2 = bc + [(hashtag, hashtag)]
            idx = Index("Hashtag #" + hashtag)
            for d in docs:
                idx += Index.Entry('{0.docid}'.format(d),
                                   '../{0.namespace}/{0.docid}'.format(d))
            self.render_index(idx, hashtag_dir, fn=hashtag, breadcrum=bc2)
