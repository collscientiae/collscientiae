# -*- coding: utf8 -*-
from __future__ import absolute_import
from .models import DocumentationModule
from .utils import get_yaml, get_markdown, create_logger
from .db import CollScientiaDB, DuplicateDocumentError
from .models import Document
from .process import ContentProcessor
from .render import OutputRenderer

import jinja2 as j2
import yaml


@j2.contextfilter
def filter_prefix(ctx, link):
    """
    Prepend level-times "../" to the given string.
    Used to go up in the directory hierarchy.
    Yes, one could also do absolute paths, but then it is harder to debug locally!
    """

    level = ctx.get("level", 0)
    if level == 0:
        return link
    path = ['..'] * level
    path.append(link)
    return '/'.join(path)


class CollScientia(object):

    """
    This is the main class, holding everything together.
    The `render()` method is starting the who process.

    """

    def __init__(self, src, theme, targ):
        from os.path import abspath, normpath, isdir

        self._log = create_logger()

        self._src = abspath(normpath(src))
        self._theme = abspath(normpath(theme))
        self._targ = abspath(normpath(targ))

        if not isdir(self.src):
            raise ValueError("src must be a directory")

        if not isdir(self.theme):
            raise ValueError("theme must be a directory")

        # setting up jinja2
        from os.path import join
        self.tmpl_dir = join(self.theme, "src")
        j2loader = j2.FileSystemLoader(self.tmpl_dir)
        self.j2env = j2.Environment(loader=j2loader, undefined=j2.StrictUndefined)
        config_theme = yaml.load(open(join(self.theme, "config.yaml")))
        if config_theme is not None:
            self.j2env.globals.update(config_theme)
        self.j2env.filters["prefix"] = filter_prefix

        # initializing all the main components
        self._db = CollScientiaDB(self)
        self.processor = ContentProcessor(self)
        self.renderer = OutputRenderer(self)
        self.config = self.read_config()
        self.j2env.globals['google_analytics'] = self.config.get('google_analytics', None)

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

    def remap_module(self, origin, target):
        """
        Uses the dictionary in the documentation configuration's
        `config.yaml` to remap the module names in order to avoid
        conflicts between them.

        :param origin: origin namespace
        :param target: target namespace to rename
        :return:
        """
        rm = self.config.get("remapping", {})
        if origin in rm:
            return rm[origin].get(target, target)
        return target

    def read_config(self):
        from os.path import join
        config_fn = join(self.src, "config.yaml")
        return get_yaml(config_fn)

    def get_documents(self):
        from os.path import join, isdir, splitext, relpath, sep
        from os import walk, listdir

        print self.config["modules"]
        for doc_dir in [join(self.src, _) for _ in self.config["modules"]]:

            mod_config = get_yaml(join(doc_dir, "config.yaml"))
            module = DocumentationModule(doc_dir, **mod_config)
            self.j2env.globals.update(mod_config)
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
                ns = module.namespace
                doc = Document(docid=docid,
                               md_raw=md_raw,
                               ns=ns)
                html, meta = self.processor.convert(doc)

                # convert to actual documents
                meta["seealso"] = [module[_] for _ in meta["seealso"]]
                doc.update(output=html, **meta)
                self.db.register(doc)

            except DuplicateDocumentError as dde:
                # add filepath and document index to error message
                m = "{:s} in {:s}".format(dde.message, filepath)
                raise DuplicateDocumentError(m)

        # after we know all the output, this hash contains everything
        self.j2env.globals["doc_root_hash"] = self.processor.get_root_hash()

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
