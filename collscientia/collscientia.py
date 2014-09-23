# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join
from .db import DB
from .models import Code, Document
from .process import Processor


def get_yaml(path, all=True):
    import yaml
    #import codecs
    #stream = codecs.open(path, "r", "utf8")
    stream = open(path, "r")
    if all:
        return yaml.load_all(stream)
    else:
        return yaml.load(stream)


class Renderer(object):

    def __init__(self, src, targ):

        self.src = abspath(normpath(src))
        self.targ = abspath(normpath(targ))

        if not isdir(self.src):
            raise ValueError("src must be a directory")

        self.processor = Processor()

        self.config = self.read_config()

    def read_config(self):
        config_fn = join(self.src, "config.yaml")
        return get_yaml(config_fn, all=False)

    def process(self, filepath):
        print "processing %s" % filepath
        docs = get_yaml(filepath)

        try:
            for d in docs:
                assert isinstance(d, Document)
                print "   -", d.id
                if hasattr(d, "content") and d.content is not None:
                    self.db.add(d)
                    for c in d.content:
                        if isinstance(c, Code):
                            print " code:", c
                        else:
                            print "    ", self.processor.process(c)

        except KeyError as ke:
            raise KeyError(ke.message + " (in %s)" % filepath)

    def build_db(self):
        self.db = DB()

        from os.path import join
        from os import walk

        for doc_module in self.config["modules"]:
            doc_dir = join(self.src, doc_module)
            for path, _, filenames in walk(doc_dir):
                for fn in filenames:
                    filepath = join(path, fn)
                    self.process(filepath)

    def render(self):
        from os import makedirs
        from os.path import exists
        from shutil import rmtree
        if exists(self.targ):
            rmtree(self.targ)
        makedirs(self.targ)

        self.build_db()

        print("rendering %s into %s" % (self.src, self.targ))


if __name__ == "__main__":
    import sys
    assert len(sys.argv) == 3,\
        "Need two arguments, first ist the source directory, the second the target directory."
    r = Renderer(sys.argv[1], sys.argv[2])
    r.render()
