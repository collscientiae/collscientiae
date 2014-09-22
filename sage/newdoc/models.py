# -*- coding: utf8 -*-
import yaml


class YAMLObjectInit(yaml.YAMLObject):

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
        fields = loader.construct_mapping(node, deep=True)
        return cls(**fields)


class DocumentationModule(YAMLObjectInit):
    yaml_tag = '!documentation'

    def __str__(self):
        return str(filter(lambda k_v: not k_v[0].startswith("_"), self.__dict__.iteritems()))


class Code(YAMLObjectInit):
    yaml_tag = "!code"

    def __init__(self, input, output=None):
        self.input = input
        self.output = output

    def test(self):
        raise NotImplementedError("this should be like a doctest")

    def __str__(self):
        return "input:\n%s\noutput: %s" % (self.input, self.output)


class Section(YAMLObjectInit):
    yaml_tag = '!section'

    def __init__(self, title, text):
        self.title = title
        self.text = text

    def __str__(self):
        return "Section %s\n%s" % (self.title, self.text)


class Document(YAMLObjectInit):

    def __init__(self, id, title, subtitle=None,
                 abstract=None,
                 area=None, content=None,
                 seealso=None):
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.abstract = abstract
        if isinstance(area, (list, tuple)):
            self.area = area
        else:
            self.area = [area]
        assert content is None or isinstance(content, list)
        self.content = content
        self.seealso = seealso


class Plot(Document):
    yaml_tag = "!plot"

    def __init__(self, code, **kwargs):
        self.code = code
        Document.__init__(self, **kwargs)


class Example(Document):
    yaml_tag = "!example"


class Reference(Document):
    yaml_tag = "!reference"


class Tutorial(Document):
    yaml_tag = "!tutorial"
