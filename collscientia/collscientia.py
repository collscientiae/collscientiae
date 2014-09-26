# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join
from collscientia.models import Code

from collscientia.utils import get_yaml
from .db import CollScientiaDB, DuplicateDocumentError
from .models import Document
from .process import ContentProcessor
from .utils import create_logger


class Renderer(object):

    def __init__(self, src, theme, targ):
        self.logger = logger = create_logger()

        self.src = abspath(normpath(src))
        self.theme = abspath(normpath(theme))
        self.targ = abspath(normpath(targ))

        if not isdir(self.src):
            raise ValueError("src must be a directory")

        if not isdir(self.theme):
            raise ValueError("theme must be a directory")

        self.db = CollScientiaDB(logger)
        self.processor = ContentProcessor(logger, self.db)

        self.config = self.read_config()

    def read_config(self):
        config_fn = join(self.src, "config.yaml")
        return get_yaml(config_fn, all=False)

    def get_documents(self):
        from os.path import join, exists
        from os import walk

        for module in self.config["modules"]:
            doc_dir = join(self.src, module)
            assert exists(doc_dir), \
                "Module '%s' does not exist." % doc_dir
            for path, _, filenames in walk(doc_dir):
                for fn in filenames:
                    filepath = join(path, fn)
                    yield module, filepath, get_yaml(filepath)

    def process(self):
        self.logger.info("building db from '%s'" % self.src)

        for module, filepath, docs in self.get_documents():
            try:
                for i, d in enumerate(docs):
                    assert isinstance(d, Document)
                    d.namespace = module
                    self.db.register(d)
                    d.output = self.processor.process(d)
                    self.logger.debug("\n" + d.output)
            except DuplicateDocumentError as dde:
                m = "{:s} in {:s}:{:d}".format(dde.message, filepath, i)
                raise DuplicateDocumentError(m)

    def output(self):
        self.logger.info("rendering into %s" % self.targ)
        for ns, docs in self.db.docs.iteritems():
            for key, doc in docs.iteritems():
                assert isinstance(doc, Document)
                out_fn = join(self.targ, ns, '.'.join([doc.id, "html"]))
                self.logger.debug(" + %s" % out_fn)

    def check_dirs(self):
        from os import makedirs
        from os.path import exists
        from shutil import rmtree
        if exists(self.targ):
            rmtree(self.targ)
        makedirs(self.targ)

    def render(self):
        self.check_dirs()
        self.process()
        self.db.check_consistency()
        self.output()


if __name__ == "__main__":
    import sys
    assert len(sys.argv) == 4,\
        "Need three arguments, first ist the source directory," \
        "the second the theme directory (containing an 'src' directory with" \
        "'static' files and the html templates) and" \
        "third is the target directory where everything is rendered into."
    r = Renderer(*sys.argv[1:])
    r.render()
