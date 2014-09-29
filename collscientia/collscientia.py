# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join
import codecs

from collscientia.utils import get_yaml, get_markdown
from .db import CollScientiaDB, DuplicateDocumentError
from .models import Document
from .process import ContentProcessor
from .utils import create_logger
from os import makedirs
from os.path import exists
from shutil import rmtree


class Renderer(object):
    module_blacklist = ["hashtag", "_tests"]

    def __init__(self, src, theme, targ):
        self.log = log = create_logger()

        self.src = abspath(normpath(src))
        self.theme = abspath(normpath(theme))
        self.targ = abspath(normpath(targ))

        if not isdir(self.src):
            raise ValueError("src must be a directory")

        if not isdir(self.theme):
            raise ValueError("theme must be a directory")

        self.db = CollScientiaDB(log)
        self.processor = ContentProcessor(log, self.db)

        self.config = self.read_config()

    def read_config(self):
        config_fn = join(self.src, "config.yaml")
        return get_yaml(config_fn, all=False)

    def get_documents(self):
        from os.path import join, exists, splitext, relpath, pathsep
        from os import walk

        for module in self.config["modules"]:
            if module in Renderer.module_blacklist:
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
                    self.log.debug("RELPATH: %s" % relpath(path, doc_dir))
                    id_path = relpath(path, doc_dir).split(pathsep)
                    if id_path[0] == ".":
                        id_path.pop(0)
                    id_path.append(basename)
                    docid = '.'.join(id_path)
                    self.log.debug("DOCID: %s" % docid)
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

    def output(self):
        self.log.info("rendering into %s" % self.targ)
        self.output_index()
        self.output_documents()
        self.output_hashtags()

    def output_index(self):
        with open(join(self.targ, "index.html"), "w") as out:
            out.write("<h1>Sections</h1><ul>")
            for ns in self.db.docs.keys():
                out.write("<li><a href='{0}/index.html'>{0}</a></li>".format(ns))
            out.write("</ul><br><br>")
            out.write("<a href='hashtag/index.html'>list of all hashtags</a>")

    def output_documents(self):
        for ns, docs in self.db.docs.iteritems():
            doc_dir = join(self.targ, ns)
            makedirs(doc_dir)

            with codecs.open(join(doc_dir, "index.html"), "w", "utf8") as out:
                out.write("""<a href="../index.html">up</a>
                <h1>{0}</h1>
                <br>
                <ul>""".format(ns))
                for key in docs.keys():
                    out.write("<li><a href='{0}.html'>{0}</a></li>".format(key))
                out.write("<ul>")

            for key, doc in docs.iteritems():
                assert isinstance(doc, Document)
                self.log.debug("  + writing %s" % doc.docid)
                out_fn = join(doc_dir, '{}.{}'.format(doc.docid, "html"))
                with codecs.open(out_fn, "w", "utf8") as out:
                    out.write(u"""<a href="../index.html">up</a> |
                    <a href="index.html">index</a>
                    <br>
                    <h1>{0.title}</h1>
                    <div><i>Abstract:</i>{0.abstract}</div>
                    <h2>Content:</h2>
                    {0.output}
                    """.format(doc))

    def output_hashtags(self):
        hashtag_dir = join(self.targ, "hashtag")
        makedirs(hashtag_dir)
        hashtags = sorted(self.db.hashtags.iteritems(),
                          key=lambda _: _[0])

        with open(join(hashtag_dir, "index.html"), "w") as out:
            out.write("""<a href="../index.html">up</a>
            <h1>Hashtags</h1>""")
            out.write("<ul>")
            for h in hashtags:
                link = "<li><a href='{0}.html'>#{0}</a></li>\n".format(h[0])
                out.write(link)
            out.write("</ul>")

        for hashtag, docs in hashtags:
            out_fn = join(hashtag_dir, '{}.{}'.format(hashtag, "html"))
            self.log.debug("  # %s" % out_fn)
            with open(out_fn, "w") as out:
                out.write("""<a href="../index.html">up</a> |
                            <a href="index.html">index</a>
                            <br>""")
                out.write("<ul>")
                for d in docs:
                    link = "<li><a href='../{0.namespace}/{0.docid}.html'>{0.docid}</a></li>"\
                        .format(d)
                    out.write(link)
                out.write("</ul>")

    def check_dirs(self):
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

    assert len(sys.argv) == 4, \
        "Need three arguments, first ist the source directory," \
        "the second the theme directory (containing an 'src' directory with" \
        "'static' files and the html templates) and" \
        "third is the target directory where everything is rendered into."
    r = Renderer(*sys.argv[1:])
    r.render()
