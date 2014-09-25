# coding=utf-8
from __future__ import absolute_import
from collections import defaultdict


class DuplicateDocumentError(Exception):

    def __init__(self, msg):
        super(DuplicateDocumentError, self).__init__(msg)


class CollScientiaDB(object):

    def __init__(self, logger):
        # maps a hashtag to list of documents
        self.logger = logger
        self.hashtags = defaultdict(list)

        # maps all IDs 1:1 to documents
        # IDs must be unique!
        self.docs = {}

    def register(self, document):
        from .models import Document
        assert isinstance(document, Document), "Given object is not a 'Document'"
        id = document.id
        ns = document.namespace
        if id in self.docs:
            raise DuplicateDocumentError("'%s'" % id)
        self.docs[id] = document
        self.logger.debug(" + %s::%s" % (ns, id))

    def register_hashtag(self, hashtag):
        self.logger.debug("   # %s" % hashtag)

    def check_consistency(self):
        self.logger.info("checking consistency")
        pass