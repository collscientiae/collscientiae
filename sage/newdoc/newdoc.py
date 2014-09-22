# -*- coding: utf8 -*-
from __future__ import absolute_import
from os.path import abspath, normpath, isdir, join
from .db import DB
from .models import Code, Document
from .process import Processor


def get_yaml(path):
    import yaml
    #import codecs
    #stream = codecs.open(path, "r", "utf8")
    stream = open(path, "r")
    return yaml.load_all(stream)


class Renderer(object):

    def __init__(self, src, targ):

        self.src = abspath(normpath(src))
        self.targ = abspath(normpath(targ))
        if not isdir(self.src):
            raise ValueError("src must be a directory")

        self.processor = Processor()

        config_fn = self.read_config()

    def read_config(self):
        config_fn = join(self.src, "config.yaml")
        return get_yaml(config_fn)

    def process(self, filepath):
        print "processing %s" % filepath
        docs = get_yaml(filepath)
        for d in docs:
            assert isinstance(d, Document)
            print "   -", d.id
            if hasattr(d, "content") and d.content is not None:
                for c in d.content:
                    if isinstance(c, Code):
                        print " code:", c
                    else:
                        print "    ", self.processor.process(c)

    def build_db(self):
        self.db = DB()

        from os.path import join
        from os import walk

        for path, _, filenames in walk(join(self.src, "doc")):
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
