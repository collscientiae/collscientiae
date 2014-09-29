# -*- coding: utf8 -*-
import yaml
import inspect
import re
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


class DocumentationModule(YAMLObjectCallingInit):
    yaml_tag = '!documentation'

    def __str__(self):
        return str(filter(lambda k_v: not k_v[0].startswith("_"), self.__dict__.iteritems()))


class Section(YAMLObjectCallingInit):
    yaml_tag = '!section'

    def __init__(self, title, text):
        self.title = title
        self.text = text

    def __str__(self):
        return "Section %s\n%s" % (self.title, self.text)


class Document(object):

    allowed_types = ["document", "tutorial", "example", "reference"]

    def __init__(self, docid, md_raw, ns=None):
        assert docid is not None and id_pattern.match(docid)
        self.docid = docid
        self._ns = ns
        self.md_raw = md_raw

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
        self.seealso = seealso
        # output contains html (or latex) after processing the content
        self.output = output
        self.authors = authors

        if tags is not None:
            if not isinstance(tags, (list, tuple)):
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


class Plot(Document):

    def __init__(self, plot, **kwargs):
        self.plot = plot
        Document.__init__(self, **kwargs)
