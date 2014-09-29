# coding=utf-8
from __future__ import absolute_import
from collections import defaultdict
from .models import Document


class DuplicateDocumentError(Exception):

    def __init__(self, msg):
        super(DuplicateDocumentError, self).__init__(msg)


class CollScientiaDB(object):

    def __init__(self, logger):
        # maps a hashtag to list of documents
        self.logger = logger
        self.hashtags = defaultdict(set)

        # maps all namespace/IDs 1:1 to documents
        # IDs must be unique across namespaces!
        self.docs = defaultdict(dict)

    def register(self, document):
        assert isinstance(document, Document), "Given object is not a 'Document'"
        docid = document.docid
        ns = document.namespace
        if docid in self.docs[ns]:
            raise DuplicateDocumentError("'%s'" % docid)
        self.docs[ns][docid] = document
        # self.logger.debug(" + %s::%s" % (ns, docid))

    def register_hashtag(self, hashtag, document):
        # self.logger.debug("   # %s" % hashtag)
        self.hashtags[hashtag].add(document)

    def check_consistency(self):
        self.logger.info("checking consistency")
        for ns, docs in self.docs.iteritems():
            for key, doc in docs.iteritems():
                assert isinstance(doc, Document)
                assert doc.namespace == ns

        # for ht, ids in self.hashtags.iteritems():
        # self.logger.debug("  #%s -> %s" % (ht, ids))
