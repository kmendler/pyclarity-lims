"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

from genologics.constants import nsmap

try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urlparse import urlsplit, urlparse, parse_qs, urlunparse

import datetime
import time
from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)

def get_sub_node(node, subnode_name):
    return next(get_sub_nodes(node, subnode_name), None)


def get_sub_nodes(node, subnode_name):
    for n in node:
        if n.tag == subnode_name:
            yield n



class XmlElement(object):
    """Abstract class providing functionality to access the root node of an instance"""
    def rootnode(self, instance):
        return instance.root

class Nestable(XmlElement):
    "Abstract base XML parser allowing the descriptor to be nested."
    def __init__(self, nesting):
        if nesting:
            self.rootkeys = nesting
        else:
            self.rootkeys = []

    def rootnode(self, instance):
        _rootnode = instance.root
        for rootkey in self.rootkeys:
            childnode = get_sub_node(_rootnode, rootkey)
            if childnode is None:
                childnode = ElementTree.Element(rootkey)
                _rootnode.append(childnode)
            _rootnode = childnode
        return _rootnode

class XmlMutable(XmlElement):
    """Class that receive the an instance so it can be mutated in place"""
    def __init__(self, instance):
        self.instance = instance


class XmlDictionary(XmlMutable, dict):
    """Class that behave like a dictionary and modify the provided instance as the dictionary gets updated"""
    def __init__(self, instance, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        XmlMutable.__init__(self, instance)
        self._update_elems()
        self._prepare_lookup()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self._setitem(key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._del_item(key)
        for node in self._elems:
            if node.attrib['name'] == key:
                self.rootnode(self.instance).remove(node)
                break

    def _prepare_lookup(self):
        for elem in self._elems:
            self._parse_element(elem)

    def clear(self):
        dict.clear(self)
        for elem in self._elems:
            self.rootnode(self.instance).remove(elem)
        self._update_elems()

    def _update_elems(self):
        raise NotImplementedError

    def _setitem(self, key, value):
        raise NotImplementedError

    def _delitem(self, key):
        raise NotImplementedError

    def _parse_element(self, element):
        raise NotImplementedError


class XmlList(XmlMutable, list):
    """Class that behave like a list and modify the provided instance as the list gets updated"""
    def __init__(self, instance, *args, **kwargs):
        XmlMutable.__init__(self, instance=instance)
        list.__init__(self, *args, **kwargs)
        self._update_elems()
        self._prepare_list()

    def _prepare_list(self):
        for elem in self._elems:
            self._parse_element(elem, lims=self.instance.lims)

    def clear(self):
        dict.clear(self)
        for elem in self._elems:
            self.rootnode(self.instance).remove(elem)
        self._update_elems()

    def __add__(self, other_list):
        for item in other_list:
            self._additem(item)
        self._update_elems()
        return list.__add__(self, other_list)

    def __iadd__(self, other_list):
        for item in other_list:
            self._additem(item)
        self._update_elems()
        return list.__iadd__(self, other_list)

    def __setitem__(self, i, item):
        if isinstance(i, slice):
            for k, v in zip(i, item):
                self._setitem(k, v)
        else:
            self._setitem(i, item)
        self._update_elems()
        return list.__setitem__(self, i, item)

    def insert(self, i, item):
        self._insertitem(i, item)
        self._update_elems()
        return list.insert(self, i, item)

    def append(self, item):
        self._additem(item)
        self._update_elems()
        return list.append(self, item)

    def extend(self, iterable):
        for v in iterable:
            self._additem(v)
        self._update_elems()
        return list.extend(self, iterable)

    def _additem(self, value):
        node = self._create_new_node(value)
        self.rootnode(self.instance).append(node)

    def _insertitem(self, index, value):
        node = self._create_new_node(value)
        self.rootnode(self.instance).insert(index, node)

    def _setitem(self, index, value):
        node = self._create_new_node(value)
        # Remove the old value in the xml
        self._delitem(index)
        # Insert it in place
        self.rootnode(self.instance).insert(index, node)

    def _delitem(self, index):
        # Remove the value in the xml and update the cached _elems
        self.rootnode(self.instance).remove(self._elems[index])

    def _update_elems(self):
        raise NotImplementedError

    def _parse_element(self, element, **kwargs):
        raise NotImplementedError

    def _create_new_node(self, value):
        raise NotImplementedError

class TagXmlList(XmlList):
    def __init__(self, instance, tag, *args, **kwargs):
        self.tag = tag
        XmlList.__init__(self, instance=instance, *args, **kwargs)

    def _update_elems(self):
        self._elems = []
        for elem in self.rootnode(self.instance):
            if elem.tag == self.tag:
                self._elems.append(elem)

class UdfDictionary(Nestable, XmlDictionary):
    "Dictionary-like container of UDFs, optionally within a UDT."

    def _is_string(self, value):
        try:
            return isinstance(value, basestring)
        except:
            return isinstance(value, str)

    def __init__(self, instance, nesting=None, **kwargs):
        Nestable.__init__(self, nesting)
        self._udt = kwargs.pop('udt', False)
        XmlDictionary.__init__(self, instance)

    def get_udt(self):
        if self._udt == True:
            return None
        else:
            return self._udt

    def set_udt(self, name):
        assert isinstance(name, str)
        if not self._udt:
            raise AttributeError('cannot set name for a UDF dictionary')
        self._udt = name
        elem = self.rootnode(self.instance).find(nsmap('udf:type'))
        assert elem is not None
        elem.set('name', name)

    udt = property(get_udt, set_udt)

    def _update_elems(self):
        self._elems = []
        if self._udt:
            elem = self.rootnode(self.instance).find(nsmap('udf:type'))
            if elem is not None:
                self._udt = elem.attrib['name']
                self._elems = elem.findall(nsmap('udf:field'))
        else:
            tag = nsmap('udf:field')
            for elem in list(self.rootnode(self.instance)):
                if elem.tag == tag:
                    self._elems.append(elem)

    def _parse_element(self, element, **kwargs):
        type = element.attrib['type'].lower()
        value = element.text
        if not value:
            value = None
        elif type == 'numeric':
            try:
                value = int(value)
            except ValueError:
                value = float(value)
        elif type == 'boolean':
            value = value == 'true'
        elif type == 'date':
            value = datetime.date(*time.strptime(value, "%Y-%m-%d")[:3])
        dict.__setitem__(self, element.attrib['name'], value)

    def _setitem(self, key, value):
        for node in self._elems:
            if node.attrib['name'] != key: continue
            vtype = node.attrib['type'].lower()

            if value is None:
                pass
            elif vtype == 'string':
                if not self._is_string(value):
                    raise TypeError('String UDF requires str or unicode value')
            elif vtype == 'str':
                if not self._is_string(value):
                    raise TypeError('String UDF requires str or unicode value')
            elif vtype == 'text':
                if not self._is_string(value):
                    raise TypeError('Text UDF requires str or unicode value')
            elif vtype == 'numeric':
                if not isinstance(value, (int, float)):
                    raise TypeError('Numeric UDF requires int or float value')
                value = str(value)
            elif vtype == 'boolean':
                if not isinstance(value, bool):
                    raise TypeError('Boolean UDF requires bool value')
                value = value and 'true' or 'false'
            elif vtype == 'date':
                if not isinstance(value, datetime.date):  # Too restrictive?
                    raise TypeError('Date UDF requires datetime.date value')
                value = str(value)
            elif vtype == 'uri':
                if not self._is_string(value):
                    raise TypeError('URI UDF requires str or punycode (unicode) value')
                value = str(value)
            else:
                raise NotImplemented("UDF type '%s'" % vtype)
            if not isinstance(value, str):
                if not self._is_string(value):
                    value = str(value).encode('UTF-8')
            node.text = value
            break
        else:  # Create new entry; heuristics for type
            if self._is_string(value):
                vtype = '\n' in value and 'Text' or 'String'
            elif isinstance(value, bool):
                vtype = 'Boolean'
                value = value and 'true' or 'false'
            elif isinstance(value, (int, float)):
                vtype = 'Numeric'
                value = str(value)
            elif isinstance(value, datetime.date):
                vtype = 'Date'
                value = str(value)
            else:
                raise NotImplementedError("Cannot handle value of type '%s'"
                                          " for UDF" % type(value))
            if self._udt:
                root = self.rootnode(self.instance).find(nsmap('udf:type'))
            else:
                root = self.rootnode(self.instance)
            elem = ElementTree.SubElement(root,
                                          nsmap('udf:field'),
                                          type=vtype,
                                          name=key)
            if not isinstance(value, str):
                if not self._is_string(value):
                    value = str(value).encode('UTF-8')

            elem.text = value

            #update the internal elements and lookup with new values
            self._update_elems()
            self._prepare_lookup()

    def _delitem(self, key):
        for node in self._elems:
            if node.attrib['name'] == key:
                self.rootnode(self.instance).remove(node)
                break


class BaseDescriptor(XmlElement):
    "Abstract base descriptor for an instance attribute."

    def __get__(self, instance, cls):
        raise NotImplementedError

class TagDescriptor(BaseDescriptor):
    """Abstract base descriptor for an instance attribute
    represented by an XML element.
    """

    def __init__(self, tag):
        self.tag = tag

    def get_node(self, instance):
        if self.tag:
            return get_sub_node(self.rootnode(instance), self.tag)
        else:
            return self.rootnode(instance)


class StringDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML element.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            return None
        else:
            return node.text

    def __set__(self, instance, value):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            # create the new tag
            node = ElementTree.Element(self.tag)
            self.rootnode(instance).append(node)
        node.text = str(value)


class StringAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        instance.get()
        return self.rootnode(instance).attrib[self.tag]

    def __set__(self, instance, value):
        instance.get()
        self.rootnode(instance).attrib[self.tag] = value


class StringListDescriptor(Nestable, TagDescriptor):
    """An instance attribute containing a list of strings
    represented by multiple XML elements.
    """
    def __init__(self, tag, nesting=None):
        Nestable.__init__(self, nesting)
        TagDescriptor.__init__(self, tag)

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in self.rootnode(instance):
            if node.tag == self.tag:
                result.append(node.text)
        return result


class StringDictionaryDescriptor(Nestable, TagDescriptor):
    """An instance attribute containing a dictionary of string key/values
    represented by a hierarchical XML element.
    """

    def __init__(self, tag, nesting=None):
        Nestable.__init__(self, nesting)
        TagDescriptor.__init__(self, tag)

    def __get__(self, instance, cls):
        instance.get()
        result = dict()
        node = get_sub_node(self.rootnode(instance), self.tag)
        if node is not None:
            for node2 in node.getchildren():
                result[node2.tag] = node2.text
        return result


class IntegerDescriptor(StringDescriptor):
    """An instance attribute containing an integer value
    represented by an XMl element.
    """

    def __get__(self, instance, cls):
        text = super(IntegerDescriptor, self).__get__(instance, cls)
        if text is not None:
            return int(text)


class IntegerAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a integer value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        instance.get()
        return int(self.rootnode(instance).attrib[self.tag])


class BooleanDescriptor(StringDescriptor):
    """An instance attribute containing a boolean value
    represented by an XMl element.
    """

    def __get__(self, instance, cls):
        text = super(BooleanDescriptor, self).__get__(instance, cls)
        if text is not None:
            return text.lower() == 'true'

    def __set__(self, instance, value):
        super(BooleanDescriptor, self).__set__(instance, str(value).lower())



class UdfDictionaryDescriptor(BaseDescriptor):
    """An instance attribute containing a dictionary of UDF values
    represented by multiple XML elements.
    """
    _UDT = False

    def __init__(self, nesting=None):
        super(BaseDescriptor, self).__init__()
        self.nesting = nesting

    def __get__(self, instance, cls):
        instance.get()
        self.value = UdfDictionary(instance, nesting=self.nesting, udt=self._UDT)
        return self.value

    def __set__(self, instance, dict_value):
        instance.get()
        udf_dict = UdfDictionary(instance, nesting=self.nesting, udt=self._UDT)
        udf_dict.clear()
        for k in dict_value:
            udf_dict[k] = dict_value[k]


class UdtDictionaryDescriptor(UdfDictionaryDescriptor):
    """An instance attribute containing a dictionary of UDF values
    in a UDT represented by multiple XML elements.
    """

    _UDT = True


class PlacementDictionary(XmlDictionary):
    def __init__(self, instance):
        XmlDictionary.__init__(self, instance)

    def _update_elems(self):
        self._elems = []
        for elem in self.rootnode(self.instance):
            if elem.tag == 'placement':
                self._elems.append(elem)

    def _parse_element(self, element, **kwargs):
        from genologics.entities import Artifact
        key = get_sub_node(element, 'value').text
        dict.__setitem__(self, key, Artifact(self.instance.lims, uri=element.attrib['uri']))

    def _setitem(self, key, value):
        if not isinstance(key, str):
            raise ValueError()
        elem1 = ElementTree.SubElement(self.rootnode(self.instance), 'placement', uri=value.uri, limsid=value.id)
        elem2 = ElementTree.SubElement(elem1, 'value')
        elem2.text = key


class PlacementDictionaryDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary of locations
    keys and artifact values represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        return PlacementDictionary(instance)

    def __set__(self, instance, dict_value):
        instance.get()
        placement_dict = PlacementDictionary(instance)
        for k in dict_value:
            placement_dict[k] = dict_value[k]


class ExternalidListDescriptor(BaseDescriptor):
    """An instance attribute yielding a list of tuples (id, uri) for
    external identifiers represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in self.rootnode(instance).findall(nsmap('ri:externalid')):
            result.append((node.attrib.get('id'), node.attrib.get('uri')))
        return result


class EntityDescriptor(TagDescriptor):
    "An instance attribute referencing another entity instance."

    def __init__(self, tag, klass):
        super(EntityDescriptor, self).__init__(tag)
        self.klass = klass

    def __get__(self, instance, cls):
        instance.get()
        node = self.rootnode(instance).find(self.tag)
        if node is None:
            return None
        else:
            return self.klass(instance.lims, uri=node.attrib['uri'])

    def __set__(self, instance, value):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            # create the new tag
            node = ElementTree.Element(self.tag)
            self.rootnode(instance).append(node)
        node.attrib['uri'] = value.uri


class EntityList(TagXmlList, Nestable):

    def __init__(self, instance, tag, klass, nesting=None, *args, **kwargs):
        Nestable.__init__(self, nesting)
        self.klass = klass
        TagXmlList.__init__(self, instance, tag, *args, **kwargs)

    def _create_new_node(self, value):
        from genologics.entities import Entity
        if not isinstance(value, Entity):
            raise TypeError('You need to provide an Entity not ' + type(value))
        node = ElementTree.Element(self.tag)
        node.attrib['uri'] = value.uri
        return node

    def _parse_element(self, element, lims, **kwargs):
        list.append(self, self.klass(lims, uri=element.attrib['uri']))


class EntityListDescriptor(Nestable, TagDescriptor):
    """An instance attribute yielding a list of entity instances
    represented by multiple XML elements.
    """

    def __init__(self, tag, klass, nesting=None):
        self.klass = klass
        Nestable.__init__(self, nesting)
        TagDescriptor.__init__(self, tag)

    def __get__(self, instance, cls):
        instance.get()
        return EntityList(instance=instance, tag=self.tag, klass=self.klass, nesting=self.rootkeys)

    def __set__(self, instance, cls, value):
        instance.get()
        el = EntityList(instance=instance, tag=self.tag, klass=self.klass, nesting=self.rootkeys)
        el.clear()
        return el.extend(value)


class AttributeList(TagXmlList, Nestable):

    def __init__(self, instance, tag, nesting, *args, **kwargs):
        Nestable.__init__(self, nesting)
        TagXmlList.__init__(self, instance, tag, *args, **kwargs)

    def _create_new_node(self, value):
        if not isinstance(value, dict):
            raise TypeError('You need to provide a dict not ' + type(value))
        node = ElementTree.Element(self.tag)
        for k, v in value.items():
            node.attrib[k] = v
        return node

    def _parse_element(self, element, lims, **kwargs):
        list.append(self, dict(element.attrib))


class AttributeListDescriptor(Nestable, TagDescriptor):
    """An instance yielding a list of dictionnaries of attributes
       for a nested xml list of XML elements"""

    def __init__(self, tag, nesting=None):
        Nestable.__init__(self, nesting)
        TagDescriptor.__init__(self, tag)

    def __get__(self, instance, cls):
        instance.get()
        return AttributeList(instance=instance, tag=self.tag, nesting=self.rootkeys)

    def __set__(self, instance, cls, value):
        instance.get()
        el = AttributeList(instance=instance, tag=self.tag, nesting=self.rootkeys)
        el.clear()
        return el.extend(value)


class DimensionDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary specifying
    the properties of a dimension of a container type.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = self.rootnode(instance).find(self.tag)
        return dict(is_alpha=node.find('is-alpha').text.lower() == 'true',
                    offset=int(node.find('offset').text),
                    size=int(node.find('size').text))


class LocationDescriptor(TagDescriptor):
    """An instance attribute containing a tuple (container, value)
    specifying the location of an analyte in a container.
    """

    def __get__(self, instance, cls):
        from genologics.entities import Container
        instance.get()
        node = self.rootnode(instance).find(self.tag)
        uri = node.find('container').attrib['uri']
        return Container(instance.lims, uri=uri), node.find('value').text


class ReagentLabelList(BaseDescriptor):
    """An instance attribute yielding a list of reagent labels"""

    def __get__(self, instance, cls):
        instance.get()
        self.value = []
        for node in self.rootnode(instance).findall('reagent-label'):
            try:
                self.value.append(node.attrib['name'])
            except:
                pass
        return self.value


class InputOutputMapList(Nestable, BaseDescriptor):
    """An instance attribute yielding a list of tuples (input, output)
    where each item is a dictionary, representing the input/output
    maps of a Process instance.
    """

    def __init__(self, nesting=None):
        Nestable.__init__(self, nesting)

    def __get__(self, instance, cls):
        instance.get()
        value = []

        for node in get_sub_nodes(self.rootnode(instance), 'input-output-map') :
            input = self.get_dict(instance.lims, get_sub_node(node, 'input'))
            output = self.get_dict(instance.lims, get_sub_node(node, 'output'))
            value.append((input, output))
        return value

    def get_dict(self, lims, node):
        from genologics.entities import Artifact, Process
        if node is None: return None
        result = dict()
        for key in ['limsid', 'output-type', 'output-generation-type']:
            try:
                result[key] = node.attrib[key]
            except KeyError:
                pass
            for uri in ['uri', 'post-process-uri']:
                try:
                    result[uri] = Artifact(lims, uri=node.attrib[uri])
                except KeyError:
                    pass
        node = get_sub_node(node, 'parent-process')
        if node is not None:
            result['parent-process'] = Process(lims, node.attrib['uri'])
        return result
