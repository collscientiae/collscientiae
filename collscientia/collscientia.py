# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join
import codecs
from collscientia.models import DocumentationModule
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
    module_blacklist = [".git", "hashtag", "_testing"]

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
        from os.path import join, exists, splitext, relpath, sep
        from os import walk, listdir

        for doc_dir in [join(self.src, _) for _ in listdir(self.src)]:
            if not isdir(doc_dir):
                continue
            mod_dir = doc_dir.split(sep)[-1]
            if mod_dir in CollScientia.module_blacklist:
                self.log.warning("skipping module '%s'" % doc_dir)
                continue

            mod_config = get_yaml(join(doc_dir, "config.yaml"))
            module = DocumentationModule(doc_dir, **mod_config)
            self.db.register_module(module)

            for path, _, filenames in walk(doc_dir):
                # self.log.debug("DOCID: %s" % docid)
                for fn in filenames:
                    if fn == "config.yaml":
                        continue
                    filepath = join(path, fn)
                    basename, ext = splitext(fn)
                    assert ext == ".md", \
                        'fn: {0} (splitext: {1})'.format(fn, ext)
                    # self.log.debug("RELPATH: %s" % relpath(path, doc_dir))
                    id_path = relpath(path, doc_dir).split(sep)
                    if id_path[0] == ".":
                        id_path.pop(0)
                    id_path.append(basename)
                    docid = '.'.join(id_path)
                    yield module, filepath, docid, get_markdown(filepath)

    def process(self):
        self.log.info("building db from '%s'" % self.src)

        for module, filepath, docid, md_raw in self.get_documents():
            try:
                doc = Document(docid=docid, md_raw=md_raw)
                html, meta = self.processor.convert(doc)
                doc.update(output=html, **meta)
                doc.namespace = module.namespace
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
        "third is the empty target directory where everything is rendered into."
    r = CollScientia(*sys.argv[1:])
    r.render()
