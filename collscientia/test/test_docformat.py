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
        with open(fn, "r") as data:
            doc, meta = self.processor.convert(data.read())
            print "\n---"
            print doc
            print "\n---"
            print meta

        fn = join(dirname(abspath(__file__)), "docformat2.md")
        with open(fn, "r") as data:
            doc, meta = self.processor.convert(data.read())
            print "\n---"
            print doc
            print "\n---"
            print meta

