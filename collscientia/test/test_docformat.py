from os.path import join, abspath, dirname
import unittest
import logging
from collscientia.process import ContentProcessor, CollScientiaDB


class DocformatTest(unittest.TestCase):

    def setUp(self):
        self.log = log = logging.getLogger("TEST")
        self.db = db = CollScientiaDB(log)
        self.processor = ContentProcessor(log, db)

    def test_one(self):
        fn = join(dirname(abspath(__file__)), "docformat.md")
        from collscientia.models import Document
        with open(fn, "r") as data:
            doc = Document("test.1", data.read())
            html, meta = self.processor.convert(doc)
            doc.update(html, **meta)
            print "\n---"
            print doc
            print "\n---"
            print meta

        fn = join(dirname(abspath(__file__)), "docformat2.md")
        with open(fn, "r") as data:
            doc = Document("test.2", data.read())
            html, meta = self.processor.convert(doc)
            doc.update(html, **meta)
            print "\n---"
            print doc
            print "\n---"
            print meta
