# coding=utf-8
from __future__ import absolute_import
from collections import defaultdict


class DB(object):

    def __init__(self):
        # maps a hashtag to list of documents
        self.hashtags = defaultdict(list)

        # maps all IDs 1:1 to documents
        # IDs must be unique!
        self.docs = {}

    def add(self, document):
        from .models import Document
        assert isinstance(document, Document), "Given object is not a 'Document'"
        id = document.id
        assert id not in self.docs.keys(), "Duplicate ID '%s'" % id
        self.docs[id] = document
