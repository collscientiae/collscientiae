# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import normpath, join, relpath, splitext, exists
from os import makedirs, walk, link
from .models import DocumentationModule, Index
from .utils import mytitle
from .models import Document


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
        """
        The one and only method which actually writes the template to disk.

        :param template_fn:
        :param target_fn:
        :param data:
        :return:
        """
        tmpl = self.cs.j2env.get_template(template_fn)
        html = tmpl.render(**data)
        with open(target_fn, "wb") as output:
            output.write(html.encode("utf-8"))
            output.write(b"\n")

    def render_index(self, index, directory, target_fn,
                     module=None, namespace=None, breadcrumb=None, level=1):
        """


        :type index: Index
        :param index:
        :param directory:
        :param target_fn:
        :param namespace:
        :param breadcrumb:
        :param level:
        :return: None
        """
        assert isinstance(index, Index)
        if not exists(directory):
            makedirs(directory)
        index_fn = join(directory, target_fn + ".html")
        self.render_template("index.html",
                             index_fn,
                             title=index.title,
                             namespace=namespace,
                             breadcrumb=breadcrumb,
                             entrytypes=Index.Entry.types,
                             module=module,
                             level=level,
                             index=index)

    def render_document_index(self, module, doc_id, cur_node, prev=None):
        """

        :type module: DocumentationModule
        :param module:
        :param doc_id:
        :param cur_node:
        :param prev:
        :return:
        """
        self.log.debug("  I %s/%s -> %s" % (module.name, doc_id, cur_node.keys()))
        assert isinstance(cur_node, DocumentationModule.Node)
        assert all(_.sort is not None for _ in cur_node.values())
        assert isinstance(module, DocumentationModule)
        first = this = None
        ns = module.namespace
        doc_dir = join(self.cs.targ, ns.lower())
        idx = Index(mytitle(module.namespace))
        for key, node in cur_node.iteritems():

            if doc_id is None:
                docid = key
            else:
                docid = doc_id + "." + key

            if docid in module:
                # there is a document, i.e. type "file"
                doc = module[docid]
                idx += Index.Entry(doc.title,
                                   docid,
                                   group=doc.group,
                                   type="file",
                                   description=doc.subtitle,
                                   node=node,
                                   sort=doc.sort)

            if len(node) > 0:
                # we have a "dir" directory
                idx += Index.Entry(node.title or mytitle(key),
                                   docid,
                                   group=None,
                                   type="dir",
                                   description=None,
                                   node=node,
                                   sort=node.sort or 0.0)

        # this is separate from above in order to obey the "sort" ordering
        for entry in idx:
            docid = entry.docid
            if docid in module:  # it's a document, set prev/next
                this = module[docid]
                if prev is not None:
                    # there is a tricky special case, where one node is a file and a dir
                    # then we don't want to have a backlink to itself.
                    this.prev = this.prev or prev
                    prev.next = this
                else:
                    first = this
                prev = this

        # we have to check for None, because there could be directories only!
        if first is not None:
            first.prev = this
            this.next = first

        if doc_id is None:
            # This is the "root" case
            fn = "index"
            self.render_index(idx,
                              doc_dir,
                              target_fn=fn,
                              module=module,
                              namespace=ns)
        else:
            fn = doc_id + ".index"
            bc = module.mk_breadcrumb(ns, doc_id)
            idx.title = " - ".join(mytitle(_[0]) for _ in reversed(bc)) + " - " + idx.title

            self.render_index(idx,
                              doc_dir,
                              target_fn=fn,
                              module=module,
                              namespace=ns,
                              breadcrumb=bc)

    def main_index(self):
        index_fn = join(self.cs.targ, "index.html")
        title = self.cs.config["title"]
        self.render_template("index_modules.html",
                             index_fn,
                             breadcrumb=[(title, "index")],
                             # modules are ordered like in the config file, OrderedDict!
                             modules=self.cs.db.modules.values())

    def document_indices(self):
        """
        This iterates through all documents and sets the .prev and .next pointers
        inside the :func:`.render_document_index` method.
        """

        self.log.info("writing document index files")

        def walk(m, node, parents, depth=0, prev=None):
            assert isinstance(m, DocumentationModule)
            # print "  " * depth, "+", key, "INDEX" if len(node) > 0 else "LEAF"

            for key, node2 in sorted(node.iteritems()):
                p = parents[:]
                p.append(key)
                walk(m, node2, p, depth=depth + 1, prev=prev)

            if len(parents) > 0:
                doc_id = ".".join(parents)
                # self.log.debug("    %s" % doc_id)
                self.render_document_index(m, doc_id, node, prev=prev)

        # this ordering is important for the prev/next chaining of documents (!)
        for ns in self.cs.config["modules"]:
            module = self.cs.db.modules[ns]
            assert isinstance(module, DocumentationModule)
            self.render_document_index(module, None, module.tree)
            walk(module, module.tree, [])

    def documents(self):
        """
        Writes all the individual documents.
        """
        self.log.info("writing document templates")
        for ns, module in self.cs.db.modules.iteritems():
            assert isinstance(module, DocumentationModule)
            doc_dir = join(self.cs.targ, ns.lower())
            # makedirs(doc_dir)

            for key, doc in module.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(doc_dir, doc.docid + ".html")
                out_src_fn = join(doc_dir, doc.docid + ".txt")
                link(doc.src_fn, out_src_fn)
                backlinks = self.cs.db.backlinks[(module.namespace, key)]
                self.log.debug("  + %s" % out_fn)
                try:
                    seealso = [module[_] for _ in doc.seealso]
                except AssertionError as ex:
                    raise Exception("Error while processing 'seealso' in '{}/{}': \"{}\""
                                    .format(ns, key, ex.message))
                bc = module.mk_breadcrumb(key, doc.docid, doc.title)
                title = " - ".join(mytitle(_[0]) for _ in reversed(bc))
                title += " - " + mytitle(ns)
                self.render_template("document.html",
                                     out_fn,
                                     namespace=ns,
                                     breadcrumb=bc,
                                     title=title,
                                     doc=doc,
                                     seealso=seealso,
                                     backlinks=backlinks,
                                     module=module,
                                     level=1)

    def hashtags(self):
        """
        Render the hashtag index and each hashtag page

        """
        self.log.info("Hashtags")
        hashtag_dir = join(self.cs.targ, "hashtag")
        hashtags = sorted(self.cs.db.hashtags.iteritems(),
                          key=lambda _: _[0])

        idx = Index("Hashtag Index")
        for ht in hashtags:
            idx += Index.Entry(ht[0], ht[0], type="hashtag")

        self.render_index(idx,
                          hashtag_dir,
                          namespace="hashtag",
                          target_fn="index")

        for hashtag, docs in hashtags:
            # out_fn = join(hashtag_dir, hashtag + ".html")
            self.log.debug("  # " + hashtag)
            bc = [(hashtag.title(), hashtag)]
            idx = Index("Hashtag #" + hashtag)
            for d in docs:
                idx += Index.Entry(d.title,
                                   d.namespace + "/" + d.docid,
                                   group=d.namespace,
                                   description=d.subtitle,
                                   prefix=1)
            self.render_index(idx,
                              hashtag_dir,
                              target_fn=hashtag,
                              namespace="hashtag",
                              breadcrumb=bc)

    def output(self):
        """
        The main method of this part, the ordering is important.
        """
        self.log.info("rendering into %s" % self.cs.targ)
        self.copy_static_files()
        self.main_index()
        self.document_indices()
        self.documents()
        self.hashtags()