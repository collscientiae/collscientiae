# coding=utf-8
from __future__ import absolute_import, unicode_literals
from collections import defaultdict
from .models import Document, DocumentationModule


class DuplicateDocumentError(Exception):

    def __init__(self, msg):
        super(DuplicateDocumentError, self).__init__(msg)


class CollScientiaDB(object):

    def __init__(self, collscientia):
        # maps a hashtag to list of documents
        self.log = collscientia.log

        # sets of backlinks (from string to document)
        self.hashtags = defaultdict(set)
        # would be cooler if these two are in DocumentationModule, but
        # it can happen that the link exists before the module exists - TODO
        self.backlinks = defaultdict(set)
        self.knowls = defaultdict(set)

        # maps all module namespaces to modules
        self.modules = {}

    def register(self, document):
        assert isinstance(document, Document), "Given object is not a 'Document'"
        docid = document.docid
        ns = document.namespace
        assert ns in self.modules,\
            "Document's namespace '{}' not registered yet!".format(ns)
        if docid in self.modules[ns]:
            raise DuplicateDocumentError("'%s'" % docid)
        self.modules[ns][docid] = document
        # self.log.debug(" + %s::%s" % (ns, docid))

    def check_consistency(self):
        self.log.info("checking consistency")
        for ns, module in self.modules.iteritems():
            for key, doc in module.iteritems():
                assert isinstance(doc, Document)
                assert doc.namespace == ns

        # for ht, ids in self.hashtags.iteritems():
        # self.log.debug("  #%s -> %s" % (ht, ids))

        for links in [self.backlinks, self.knowls]:
            for (ns, docid), docs in links.iteritems():
                assert ns in self.modules,\
                    "illegal namespace '{}' in a knowl or link to {}".format(ns, docs)
                assert docid in self.modules[ns],\
                    "unkown ID '{}' in a knowl or link to {}".format(docid, docs)

    def register_module(self, module):
        assert isinstance(module, DocumentationModule)
        assert module.namespace not in self.modules
        self.modules[module.namespace] = module

    def register_hashtag(self, hashtag, document):
        # self.log.debug("   # %s" % hashtag)
        self.hashtags[hashtag].add(document)

    def register_knowl(self, ns, knowl_id, document):
        self.knowls[(ns, knowl_id)].add(document)

    def register_link(self, ns, link_id, document):
        # don't register links to itself
        if document.namespace == ns and document.docid == link_id:
            return
        self.backlinks[(ns, link_id)].add(document)
