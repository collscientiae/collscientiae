from os.path import join, abspath, dirname
import unittest
import logging
from collscientiae.collscientia import CollScientia
from collscientiae.process import ContentProcessor, CollScientiaeDB


class DocformatTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from tempfile import mkdtemp
        from os.path import join
        cls.src = mkdtemp()
        with open(join(cls.src, "config.yaml"), "w") as cy:
            cy.write("")

        cls.theme = mkdtemp()
        with open(join(cls.theme, "config.yaml"), "w") as cy:
            cy.write("")

        cls.targ = mkdtemp()

    @classmethod
    def tearDownClass(cls):
        from shutil import rmtree
        rmtree(cls.src)
        rmtree(cls.targ)
        rmtree(cls.theme)

    def setUp(self):
        self.cs = cs = CollScientia(DocformatTest.src,
                                    DocformatTest.theme,
                                    DocformatTest.targ)
        cs._log = logging.getLogger("TEST")
        self.db = db = CollScientiaeDB(cs)
        self.processor = ContentProcessor(cs)

    def test_one(self):
        fn = join(dirname(abspath(__file__)), "docformat.md")
        from collscientiae.models import Document
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
