# coding=utf-8
from __future__ import absolute_import, unicode_literals
from collections import defaultdict, OrderedDict


class DuplicateDocumentError(Exception):

    def __init__(self, msg):
        super(DuplicateDocumentError, self).__init__(msg)


class CollScientiaeDB(object):

    def __init__(self, collscientiae):
        self.log = collscientiae.log

        # would be cooler if these two are in DocumentationModule, but
        # it can happen that the link exists before the module exists - TODO
        # maps a hashtag to list of documents
        self.hashtags = defaultdict(set)
        # sets of backlinks (from string to document)
        self.backlinks = defaultdict(set)
        self.knowls = defaultdict(set)

        # maps all module namespaces to modules
        self.modules = OrderedDict()

    def register(self, document):
        from .models import Document
        assert isinstance(document, Document), "Given object is not a 'Document'"
        ns = document.namespace
        assert ns in self.modules,\
            "Document's namespace '{}' not registered yet!".format(ns)
        self.modules[ns].add_document(document)
        # self.log.debug(" + %s::%s" % (ns, docid))

    def check_consistency(self):
        from .models import Document
        self.log.info("checking consistency")
        for ns, module in self.modules.iteritems():
            # titles = {}
            for key, doc in module.iteritems():
                assert isinstance(doc, Document)
                assert doc.namespace == ns
                # assert doc.title not in titles, \
                #    "Duplicate title '{0:s}' in {1:s}/{2:s} and {3:s}" \
                #    .format(doc.title, ns, key, titles[doc.title])
                # titles[doc.title] = doc.docid
                node = module.tree
                for level in doc.docid.split("."):
                    node = node[level]
                if len(node) == 0:
                    assert level != "index",\
                        "There is the document {}/{} with the docid ending in '{}'!"\
                        .format(key, doc, level)

        # for ht, ids in self.hashtags.iteritems():
        # self.log.debug("  #%s -> %s" % (ht, ids))

        for links in [self.backlinks, self.knowls]:
            for (ns, docid), docs in links.iteritems():
                assert ns in self.modules,\
                    "illegal namespace '{}' in a knowl or link to {}".format(ns, docs)
                assert docid in self.modules[ns],\
                    "unkown ID '{}' in a knowl or link to {}".format(docid, docs)

    def register_module(self, module):
        from .models import DocumentationModule
        assert isinstance(module, DocumentationModule)
        assert module.namespace not in self.modules
        self.modules[module.namespace] = module

    def register_hashtag(self, hashtag, document):
        # self.log.debug("   # %s" % hashtag)
        self.hashtags[hashtag].add(document)

    def register_knowl(self, ns, knowl_id, document):
        self.knowls[(ns, knowl_id)].add(document)
        self.register_link(ns, knowl_id, document)

    def register_link(self, ns, link_id, document):
        # don't register links to itself
        if document.namespace == ns and document.docid == link_id:
            return
        self.backlinks[(ns, link_id)].add(document)
