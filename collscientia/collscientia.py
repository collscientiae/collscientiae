# -*- coding: utf8 -*-
from __future__ import absolute_import, unicode_literals
from os.path import abspath, normpath, isdir, join
import codecs
from .utils import get_yaml, get_markdown, create_logger
from .db import CollScientiaDB, DuplicateDocumentError
from .models import Document
from .process import ContentProcessor
from .render import OutputRenderer
from os.path import exists
from shutil import rmtree
from os import makedirs


class CollScientia(object):

    """
    This is the main class of this module.


    """
    module_blacklist = ["hashtag", "tests"]

    def __init__(self, src, theme, targ):
        self._log = create_logger()

        self._src = abspath(normpath(src))
        self._theme = abspath(normpath(theme))
        self._targ = abspath(normpath(targ))

        if not isdir(self.src):
            raise ValueError("src must be a directory")

        if not isdir(self.theme):
            raise ValueError("theme must be a directory")

        self._db = CollScientiaDB(self)
        self.processor = ContentProcessor(self)
        self.renderer = OutputRenderer(self)
        self.config = self.read_config()

    @property
    def log(self):
        return self._log

    @property
    def src(self):
        return self._src

    @property
    def targ(self):
        return self._targ

    @property
    def theme(self):
        return self._theme

    @property
    def db(self):
        return self._db

    def read_config(self):
        config_fn = join(self.src, "config.yaml")
        return get_yaml(config_fn, all=False)

    def get_documents(self):
        from os.path import join, exists, splitext, relpath, pathsep
        from os import walk

        for module in self.config["modules"]:
            if module in CollScientia.module_blacklist:
                raise ValueError("module %s not allowed")
            doc_dir = join(self.src, module)
            assert exists(doc_dir), \
                "Module '%s' does not exist." % doc_dir
            for path, _, filenames in walk(doc_dir):
                for fn in filenames:
                    filepath = join(path, fn)
                    # yield module, filepath, get_yaml(filepath)
                    basename, ext = splitext(fn)
                    assert ext == ".md", \
                        'fn: {0:s} (splitext: {1:s})'.format(fn, ext)
                    # self.log.debug("RELPATH: %s" % relpath(path, doc_dir))
                    id_path = relpath(path, doc_dir).split(pathsep)
                    if id_path[0] == ".":
                        id_path.pop(0)
                    id_path.append(basename)
                    docid = '.'.join(id_path)
                    # self.log.debug("DOCID: %s" % docid)
                    yield module, filepath, docid, get_markdown(filepath)

    def process(self):
        self.log.info("building db from '%s'" % self.src)

        for module, filepath, docid, md_raw in self.get_documents():
            try:
                doc = Document(docid=docid, md_raw=md_raw)
                html, meta = self.processor.convert(doc)
                doc.update(output=html, **meta)
                doc.namespace = module
                self.db.register(doc)

            except DuplicateDocumentError as dde:
                # add filepath and document index to error message
                m = "{:s} in {:s}".format(dde.message, filepath)
                raise DuplicateDocumentError(m)

    def check_dirs(self):
        if exists(self.targ):
            rmtree(self.targ)
        makedirs(self.targ)

    def render(self):
        self.check_dirs()
        self.process()
        self.db.check_consistency()
        self.renderer.output()


if __name__ == "__main__":
    import sys

    assert len(sys.argv) == 4, \
        "Need three arguments, first ist the source directory," \
        "the second the theme directory (containing an 'src' directory with" \
        "'static' files and the html templates) and" \
        "third is the target directory where everything is rendered into."
    r = CollScientia(*sys.argv[1:])
    r.render()
