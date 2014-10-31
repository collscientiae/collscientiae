# -*- coding: utf8 -*-
from collections import defaultdict
import yaml
import inspect
import re
from .utils import indexsort
from .db import DuplicateDocumentError

namespace_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]+$")
id_pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")


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

    class Node(defaultdict):

        @staticmethod
        def recursive_dict():
            return DocumentationModule.Node(DocumentationModule.Node.recursive_dict)

        def __init__(self, default_factory=None):
            if default_factory is None:
                default_factory = DocumentationModule.Node.recursive_dict
            defaultdict.__init__(self, default_factory)
            self.title = None
            self.sort = 0.0

        def update(self, config):
            self.__dict__.update(**config)

    def __init__(self, path, **config):
        # name and description are mandatory entries
        self.name = config.pop("name")
        self.description = config.pop("description")
        self.landing_page = None
        self.latex_macros = None
        if "landing_page" in config:
            self.landing_page = config.pop("landing_page")
        assert "path" not in config
        assert "namespace" not in config
        self.__dict__.update(**config)
        self.path = path
        from os.path import sep
        self.namespace = path.split(sep)[-1]
        # maps to documents via their unique ID
        self._documents = {}
        # tree of document IDs (key mapping to empty dict indicates a leaf)
        self.tree = DocumentationModule.Node()

    def __getitem__(self, key):
        assert key in self._documents,\
            "Document '%s' does not exist in module '%s'" % (key, self.namespace)

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

    def mk_breadcrum(self, ns, docid, title=None):
        ret = []
        ids = docid.split(".")
        node = self.tree
        for level, name in enumerate(ids):
            node = node[name]
            part_id = '.'.join(ids[:level + 1])
            if level < len(ids) - 1:
                n = node.title or name.title()
                part_id += ".index"
            else:
                n = title or node.title or ids[-1].title()
            ret.append((n, part_id))
        return ret


class Section(YAMLObjectCallingInit):
    yaml_tag = '!section'

    def __init__(self, title, text):
        self.title = title
        self.text = text

    def __str__(self):
        return "Section %s\n%s" % (self.title, self.text)


class Document(object):

    allowed_types = ["document", "tutorial", "example", "reference"]

    def __init__(self, docid, md_raw, ns, src_fn):
        assert docid is not None and id_pattern.match(docid),\
            "docid: '%s'" % docid
        self.docid = docid
        self._ns = ns
        self.md_raw = md_raw
        self.src_fn = src_fn

        # need to be set after *all* documents are processed
        self.backlinks = None
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
        self.group = None
        self.sort = 0.0
        # pointers to next/previous documents for links on the website
        self.prev = self.next = None

    def update(self, output, title=None, authors=None,
               subtitle=None, abstract=None,
               tags=None, type=None, group=None,
               seealso=None, sort=None):
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
        if sort:
            self.sort = float(sort)

        if tags is not None and not isinstance(tags, (list, tuple)):
            tags = [tags]
        self.tags = tags
        self.group = group

    @property
    def namespace(self):
        assert self._ns is not None
        return self._ns

    @namespace.setter
    def namespace(self, ns):
        assert self._ns is None, "Namespace can only be set once"
        assert namespace_pattern.match(ns)
        self._ns = ns

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

        * `title`: Title
        * `group`: if given, the output index is grouped by this
        * `docid`: the document ID to reference to
        * `description`: e.g. the subtitle of a document
        * `type`: directory, file or hashtag
        * `prefix`: prefixing the referenced link, usually 0 (?)
        * `sort`: a floating point number, used in :func:`.utils.indexsort` to break
                  strict alphabetical sorting.
        """

        __slots__ = ["title", "group", "docid", "description", "type", "prefix", "sort", "node"]

        types = ("dir", "file", "hashtag")

        def __init__(self, title, docid,
                     group=None, description=None, type="file", sort=None, node=None, prefix=0):
            assert type in Index.Entry.types
            self.title = title
            self.group = group
            self.docid = docid
            self.description = description
            self.type = type
            self.sort = sort
            self.node = node
            self.prefix = prefix

        @property
        def href(self):
            h = ''.join(["../"] * self.prefix)
            h += self.docid
            if self.type == "dir":
                h += ".index"
            return h

    def __init__(self, title):
        self.title = title
        self.entries = []

    def __iadd__(self, entry):
        assert isinstance(entry, Index.Entry)
        self.entries.append(entry)
        return self

    def __iter__(self):
        return iter(indexsort(self.entries))
