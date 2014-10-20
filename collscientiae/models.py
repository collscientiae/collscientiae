# -*- coding: utf8 -*-
from collections import defaultdict
import yaml
import inspect
import re
from .db import DuplicateDocumentError

namespace_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]+$")
id_pattern = re.compile(r"^[a-zA-Z0-9_.]+$")


class YAMLObjectCallingInit(yaml.YAMLObject):

    """
    This overrides the :meth:`yaml.YAMLObject.from_from_yaml` method in such a way,
    that instead of only updating the __dict__,
    it properly calls the `__init__` constructor.
    (That's not done by default, no idea why -- it produces more errors for missing
    init-arguments, etc., though.)

    Note::

        This assumes that the classes do not implement their own `__setstate__`.
    """

    @classmethod
    def from_yaml(cls, loader, node):
        # get expected fields and throw a proper exception if a field is missing
        argspec = inspect.getargspec(cls.__init__)
        expected = argspec.args
        if argspec.defaults is not None:
            # getting rid of arguments with defaults
            expected = expected[:-len(argspec.defaults)]
        expected.remove("self")
        # this is from the usual yaml loader
        fields = loader.construct_mapping(node, deep=True)
        # continuing to check keyword arguments
        actual = set(fields.keys())
        for arg in expected:
            if arg not in actual:
                raise KeyError("Missing Data: '%s' missing." % arg)
        # calling the class constructor properly
        return cls(**fields)


class DocumentationModule(object):

    def __init__(self, path, **config):
        # name and description are mandatory entries
        self.name = config.pop("name")
        self.description = config.pop("description")
        assert "path" not in config
        assert "namespace" not in config
        self.__dict__.update(**config)
        self.path = path
        from os.path import sep
        self.namespace = path.split(sep)[-1]
        # maps to documents via their unique ID
        self._documents = {}
        # tree of document IDs (key mapping to empty dict indicates a leaf)
        recursive_dict = lambda: defaultdict(recursive_dict)
        self.tree = defaultdict(recursive_dict)

    def __getitem__(self, key):
        return self._documents[key]

    def __setitem__(self, key, item):
        self._documents[key] = item

    def add_document(self, document):
        assert isinstance(document, Document), "Given object is not a 'Document'"
        docid = document.docid
        if docid in self:
            raise DuplicateDocumentError("'%s'" % docid)
        self[docid] = document
        node = self.tree
        for level in docid.split("."):
            node = node[level]

    def iteritems(self):
        return self._documents.iteritems()

    def keys(self):
        return self._documents.keys()

    def __contains__(self, item):
        return item in self._documents

    def __str__(self):
        return "Module {}".format(self.name)


class Section(YAMLObjectCallingInit):
    yaml_tag = '!section'

    def __init__(self, title, text):
        self.title = title
        self.text = text

    def __str__(self):
        return "Section %s\n%s" % (self.title, self.text)


class Document(object):

    allowed_types = ["document", "tutorial", "example", "reference"]

    def __init__(self, docid, md_raw, ns):
        assert docid is not None and id_pattern.match(docid)
        self.docid = docid
        self._ns = ns
        self.md_raw = md_raw
        self.backlinks = None  # need to be set after *all* documents are processed
        # these are defined in self.update(...)
        self.type = None
        self.title = None
        self.subtitle = None
        self.abstract = None
        self.seealso = None
        # output contains html (or latex) after processing the content
        self.output = None
        self.authors = None
        self.tags = None

    def update(self, output, title=None, authors=None,
               subtitle=None, abstract=None,
               tags=None, type=None,
               seealso=None):
        assert type and type in Document.allowed_types,\
            "type is '%s'" % type
        self.type = type
        self.title = title
        self.subtitle = subtitle
        self.abstract = abstract
        self.seealso = seealso or []
        # output contains html (or latex) after processing the content
        self.output = output
        self.authors = authors

        if tags is not None and not isinstance(tags, (list, tuple)):
            tags = [tags]
        self.tags = tags

    @property
    def namespace(self):
        assert self._ns is not None
        return self._ns

    @namespace.setter
    def namespace(self, ns):
        assert self._ns is None, "Namespace can only be set once"
        assert namespace_pattern.match(ns)
        self._ns = ns

    @staticmethod
    def mk_breadcrum(docid, title=None):
        ret = []
        ids = docid.split(".")
        for level, name in enumerate(ids):
            part_id = '.'.join(ids[:level + 1])
            if level < len(ids) - 1:
                n = name.title()
            else:
                n = title or ids[-1].title()
            ret.append((n, part_id))
        return ret

    def breadcrum(self):
        """
        :return: list of [("name", "link.to.it"), ...]
        """
        return self.mk_breadcrum(self.docid, self.title)

    def __repr__(self):
        return "Document[{0.namespace}/{0.docid}]".format(self)


class Plot(Document):

    def __init__(self, plot, **kwargs):
        self.plot = plot
        Document.__init__(self, **kwargs)


class Index(object):

    """
    Simple container class, contains the data for all those indexing pages.
    Its only use is to send the info to the template.
    """
    class Entry(object):

        """
        One single index entry
        """

        __slots__ = ["title", "href", "description", "type"]

        types = ("dir", "file", "hashtag")

        def __init__(self, title, href, description=None, type="file"):
            assert type in Index.Entry.types
            self.title = title
            self.href = href + ".html"
            self.description = description
            self.type = type

    def __init__(self, title):
        self.title = title
        self.entries = []

    def __iadd__(self, entry):
        assert isinstance(entry, Index.Entry)
        self.entries.append(entry)
        return self

    def __iter__(self):
        return iter(self.entries)
