# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join, relpath, splitext, exists
from os import makedirs, walk, link
from collscientiae.models import DocumentationModule, Index
from collscientiae.utils import mytitle
from .models import Document
import codecs


class OutputRenderer(object):

    def __init__(self, collscientiae):
        self.log = collscientiae.log
        self.cs = collscientiae

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

    def render_template(self, template_fn, target_fn, **data):
        tmpl = self.cs.j2env.get_template(template_fn)
        html = tmpl.render(**data)
        with open(target_fn, "wb") as output:
            output.write(html.encode("utf-8"))
            output.write(b"\n")

    def render_index(self, index, directory, target_fn, namespace=None, breadcrum=None, level=1):
        assert isinstance(index, Index)
        if not exists(directory):
            makedirs(directory)
        index_fn = join(directory, target_fn + ".html")
        self.render_template("index.html",
                             index_fn,
                             title=index.title,
                             namespace=namespace,
                             breadcrum=breadcrum,
                             entrytypes=Index.Entry.types,
                             level=level,
                             index=index)

    def render_document_index(self, module, doc_id, children):
        assert isinstance(module, DocumentationModule)
        ns = module.namespace
        doc_dir = join(self.cs.targ, ns)
        idx = Index(mytitle(module.namespace))
        for key, node in children.iteritems():
            type = "dir" if len(node) > 0 else "file"
            sort = None
            group = None
            if doc_id is None:
                docid = key
            else:
                docid = doc_id + "." + key
            if type == "file":
                doc = module[docid]
                descr = doc.subtitle
                title = doc.title
                sort = doc.sort
                group = doc.group
            else:
                descr = None
                title = mytitle(key)
            idx += Index.Entry(title,
                               docid,
                               group=group,
                               type=type,
                               description=descr,
                               sort=sort)

        bc = []
        if doc_id is None:
            fn = "index"
        else:
            fn = doc_id
            bc = Document.mk_breadcrum(doc_id)
            idx.title = " - ".join(mytitle(_[0]) for _ in reversed(bc)) + " - " + idx.title

        self.render_index(idx,
                          doc_dir,
                          target_fn=fn,
                          namespace=ns,
                          breadcrum=bc)

    def output(self):
        self.log.info("rendering into %s" % self.cs.targ)
        self.copy_static_files()
        self.main_index()
        self.documents()
        self.document_indices()
        self.hashtags()

    def main_index(self):
        index_fn = join(self.cs.targ, "index.html")
        title = self.cs.config["title"]
        # ordered, like in the config file!
        modules = [self.cs.db.modules[_] for _ in self.cs.config["modules"]]
        self.render_template("index_modules.html",
                             index_fn,
                             title=title,
                             modules=modules)

    def document_indices(self):
        self.log.info("writing document index files")

        def walk(m, node, parents, depth=0):
            assert isinstance(m, DocumentationModule)
            # print "  " * depth, "+", key, "INDEX" if len(node) > 0 else "LEAF"
            if len(parents) > 0:
                doc_id = ".".join(parents)
                self.log.debug("    %s" % doc_id)
                if doc_id not in m:
                    self.render_document_index(m, doc_id, node)

            for key, node in node.iteritems():
                p = parents[:]
                p.append(key)
                walk(m, node, p, depth=depth + 1)

        for ns, module in self.cs.db.modules.iteritems():
            assert isinstance(module, DocumentationModule)
            self.log.debug("  I %s" % module.name)
            self.render_document_index(module, None, module.tree)
            walk(module, module.tree, [])

    def documents(self):
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
                try:
                    seealso = [module[_] for _ in doc.seealso]
                except AssertionError as ex:
                    raise Exception("Error while processing 'seealso' in '{}/{}': \"{}\""
                                    .format(ns, key, ex.message))
                bc = doc.breadcrum()
                title = " - ".join(mytitle(_[0]) for _ in reversed(bc))
                title += " - " + mytitle(ns)
                self.render_template("document.html",
                                     out_fn,
                                     namespace=ns,
                                     breadcrum=bc,
                                     title=title,
                                     doc=doc,
                                     seealso=seealso,
                                     backlinks=backlinks,
                                     level=1)

    def hashtags(self):
        self.log.info("Hashtags")
        hashtag_dir = join(self.cs.targ, "hashtag")
        hashtags = sorted(self.cs.db.hashtags.iteritems(),
                          key=lambda _: _[0])

        idx = Index("Hashtag Index")
        for ht in hashtags:
            idx += Index.Entry(ht[0], ht[0], type="hashtag")

        bc = [("#", "index")]
        self.render_index(idx, hashtag_dir, target_fn="index", breadcrum=bc)

        for hashtag, docs in hashtags:
            # out_fn = join(hashtag_dir, hashtag + ".html")
            self.log.debug("  # " + hashtag)
            bc2 = bc + [(hashtag.title(), hashtag)]
            idx = Index("Hashtag #" + hashtag)
            for d in docs:
                idx += Index.Entry(d.title,
                                   d.namespace + "/" + d.docid,
                                   group=d.namespace,
                                   description=d.subtitle,
                                   prefix=1)
            self.render_index(idx, hashtag_dir, target_fn=hashtag, breadcrum=bc2)
