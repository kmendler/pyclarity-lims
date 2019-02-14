"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""
from decimal import Decimal

from pyclarity_lims.constants import nsmap

try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urlparse import urlsplit, urlparse, parse_qs, urlunparse

import datetime
import time
from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)


class XmlElement(object):
    """Abstract class providing functionality to access the root node of an instance"""
    def rootnode(self, instance):
        return instance.root


class Nestable(XmlElement):
    """Abstract base XML parser allowing the descriptor to be nested."""
    def __init__(self, nesting):
        if nesting:
            self.rootkeys = nesting
        else:
            self.rootkeys = []

    def rootnode_from_root(self, root):
        _rootnode = root
        for rootkey in self.rootkeys:
            childnode = _rootnode.find(rootkey)
            if childnode is None:
                childnode = ElementTree.Element(rootkey)
                _rootnode.append(childnode)
            _rootnode = childnode
        return _rootnode

    def rootnode(self, instance):
        return self.rootnode_from_root(instance.root)


class XmlMutable(XmlElement):
    """Class that receive an instance so it can be mutated in place"""
    def __init__(self, instance):
        self.instance = instance


# Dictionary types
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
        self._update_elems()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._delitem(key)
        self._update_elems()

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


class UdfDictionary(Nestable, XmlDictionary):
    """Dictionary-like container of UDFs, optionally within a UDT."""

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
        if self._udt is True:
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
                if not isinstance(value, (int, float, Decimal)):
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
            elif isinstance(value, (int, float, Decimal)):
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

    def _delitem(self, key):
        for node in self._elems:
            if node.attrib['name'] == key:
                self.rootnode(self.instance).remove(node)
                break


class XmlElementAttributeDict(XmlDictionary, Nestable):
    """
    Dictionary of attributes for a specific xml element.
    It will find all the elements with the specified tag and use the one in the provided position
    then put all attributes of that tag in a dict.
    The key is the attribute's name and value is the attribute's value.
    """

    def __init__(self, instance, tag, *args, **kwargs):
        self.position = kwargs.pop('position', 0)
        self.tag = tag
        Nestable.__init__(self, nesting=kwargs.pop('nesting', []))
        XmlDictionary.__init__(self, instance, *args, **kwargs)

    def _update_elems(self):
        # only one element here
        # find all the tags
        all_tags = self.rootnode(self.instance).findall(self.tag)
        # only take the one at specified position
        if len(all_tags) > self.position:
            self._elems = [all_tags[self.position]]
        else:
            self._elems = []

    def _parse_element(self, element, **kwargs):
        for k, v in element.attrib.items():
            dict.__setitem__(self, k, v)

    def _setitem(self, key, value):
        self._elems[0].attrib[key] = value

    def _delitem(self, key):
        del self._elems[0].attrib[key]


class XmlAction(XmlElementAttributeDict):
    """
    One Action of a list of actions. The Action is stored in an XmlElementAttributeDict with specific keys.
    artifact: The Artifact associated with this Action
    step: The next step associated with this action
    rework-step: The step associated with this action when the Artifact needs to be requeued
    action: The type of action to perform. (leave, repeat, remove, review, complete, store, nextstep, rework, completerepeat, unknown)
    """
    def _parse_element(self, element, **kwargs):
        from pyclarity_lims.entities import Artifact, ProtocolStep
        for k, v in element.attrib.items():

            if k == 'artifact-uri':
                k = 'artifact'
                v = Artifact(self.instance.lims, uri=v)
            elif k in ('step-uri', 'rework-step-uri'):
                k = k[:-(len('-uri'))]
                v = ProtocolStep(self.instance.lims, uri=v)
            dict.__setitem__(self, k, v)

    def _setitem(self, key, value):
        from pyclarity_lims.entities import Artifact, ProtocolStep
        if (key in ['artifact'] and isinstance(value, Artifact)) or \
           (key in ['step', 'rework-step'] and isinstance(value, ProtocolStep)):
            key += '-uri'
            value = value.uri
        elif key in ['action']:
            pass
        else:
            raise KeyError('%s is not a supported key for next action' % key)
        self._elems[0].attrib[key] = value

    def _delitem(self, key):
        if key in ['artifact', 'step', 'rework-step']:
            key = key + '-uri'
        del self._elems[0].attrib[key]


class PlacementDictionary(XmlDictionary):
    """Dictionary of placements in a Container.
    The key is the location such as "A:1"
    and the value is the artifact in that well/tube.
    """

    def _update_elems(self):
        self._elems = self.rootnode(self.instance).findall('placement')

    def _parse_element(self, element, **kwargs):
        from pyclarity_lims.entities import Artifact
        key = element.find('value').text
        dict.__setitem__(self, key, Artifact(self.instance.lims, uri=element.attrib['uri']))

    def _setitem(self, key, value):
        if not isinstance(key, str):
            raise ValueError()
        elem1 = None
        for node in self._elems:
            if node.find('value').text == key:
                elem1 = node
                break
        if elem1:
            self.rootnode(self.instance).remove(elem1)
        elem1 = ElementTree.SubElement(self.rootnode(self.instance), 'placement', uri=value.uri, limsid=value.id)
        elem2 = ElementTree.SubElement(elem1, 'value')
        elem2.text = key

    def _delitem(self, key):
        for node in self._elems:
            if node.find('value').text == key:
                self.rootnode(self.instance).remove(node)
                break


class SubTagDictionary(XmlDictionary, Nestable):
    """Dictionary of xml sub elements where the key is the tag
    and the value is the text of the sub element.
    """
    def __init__(self, instance, tag, **kwargs):
        # In case extra nesting is provided
        nesting = kwargs.get('nesting', [])
        nesting.append(tag)
        Nestable.__init__(self, nesting=nesting)
        XmlDictionary.__init__(self, instance)

    def _update_elems(self):
        root_node = self.rootnode(self.instance)
        if root_node:
            self._elems = root_node.getchildren()
        else:
            self._elems = []

    def _parse_element(self, element, **kwargs):
        dict.__setitem__(self, element.tag, element.text)

    def _setitem(self, key, value):
        if not isinstance(key, str):
            raise ValueError()
        root_node = self.rootnode(self.instance)

        elem = root_node.find(key)
        if elem is None:
            elem = ElementTree.SubElement(root_node, key)
        elem.text = value

    def _delitem(self, key):
        root_node = self.rootnode(self.instance)
        for node in self._elems:
            if node.tag == key:
                root_node.remove(node)
                break


class XmlPooledInputDict(XmlDictionary, Nestable):
    """Dictionary where the key is the pool name and the value a tuple of (pool, inputs).
    The first item of the tuple is an output Artifact representing the pool, and
    the second item is a tuple containing the input artifacts for that pool.
    """

    def __init__(self, instance, *args, **kwargs):
        Nestable.__init__(self, nesting=['pooled-inputs'])
        XmlDictionary.__init__(self, instance, *args, **kwargs)

    def _update_elems(self):
        self._elems = self.rootnode(self.instance).findall('pool')

    def _setitem(self, key, value):
        if not isinstance(key, str):
            raise ValueError()
        if not isinstance(value, tuple) or not len(value) == 2:
            raise TypeError('You need to provide a tuple of 2 elements not ' + type(value))
        pool, list_input = value
        self._delitem(key)
        node = ElementTree.SubElement(self.rootnode(self.instance), 'pool')
        node.attrib['name'] = key
        if pool and pool.uri:
            node.attrib['output-uri'] = pool.uri
        for inart in list_input:
            sub = ElementTree.Element('input')
            sub.attrib['uri'] = inart.uri
            node.append(sub)

    def _delitem(self, key):
        for node in self._elems:
            if node.attrib['name'] == key:
                self.rootnode(self.instance).remove(node)
                break

    def _parse_element(self, element, **kwargs):
        from pyclarity_lims.entities import Artifact
        if 'output-uri' in element.attrib:
            pool = Artifact(self.instance.lims, uri=element.attrib.get('output-uri'))
        else:
            pool = None
        dict.__setitem__(
            self,
            element.attrib.get('name'),
            (
                pool,
                tuple(Artifact(self.instance.lims, uri=sub.attrib.get('uri')) for sub in element.findall('input'))
            )
        )


# List types
class XmlList(XmlMutable, list):
    """Class that behaves like a list and modifies the provided instance as the list gets updated"""
    def __init__(self, instance, *args, **kwargs):
        XmlMutable.__init__(self, instance=instance)
        list.__init__(self, *args, **kwargs)
        self._update_elems()
        self._prepare_list()

    def _prepare_list(self):
        for i, elem in enumerate(self._elems):
            self._parse_element(elem, lims=self.instance.lims, position=i)

    def clear(self):
        # python 2.7 does not have a clear function for list
        del self[:]
        for elem in self._elems:
            self.rootnode(self.instance).remove(elem)
        self._update_elems()

    def __add__(self, other_list):
        for item in other_list:
            self._additem(item)
        self._update_elems()
        return list.__add__(self, [self._modify_value_before_insert(v, len(self) + i) for i, v in enumerate(other_list)])

    def __iadd__(self, other_list):
        for item in other_list:
            self._additem(item)
        self._update_elems()
        return list.__iadd__(self, [self._modify_value_before_insert(v, len(self) + i) for i, v in enumerate(other_list)])

    def __setitem__(self, i, item):
        if isinstance(i, slice):
            new_items = []
            slice_range = range(*i.indices(len(self)))
            if len(slice_range) != len(item):
                raise ValueError('Setting slice and list of different sizes is not supported: %s != %s' % (len(slice_range), len(item)))
            for k, v in zip(slice_range, item):
                self._setitem(k, v)
                new_items.append(self._modify_value_before_insert(v, k))
            item = new_items
        elif isinstance(i, int):
            self._setitem(i, item)
            item = self._modify_value_before_insert(item, i)
        else:
            raise TypeError('List indices must be integers or slices, not ' + type(i))
        self._update_elems()
        return list.__setitem__(self, i, item)

    def insert(self, i, item):
        self._insertitem(i, item)
        self._update_elems()
        list.insert(self, i, self._modify_value_before_insert(item, i))
        # Hack to make sure subsequent elements get updated if they went through _modify_value_before_insert
        new_items = []
        for p, v in enumerate(self[i + 1:]):
            new_items.append(self._modify_value_before_insert(v, i + 1 + p))
        list.__setitem__(self, slice(i + 1, len(self), 1), new_items)

    def append(self, item):
        self._additem(item)
        self._update_elems()
        return list.append(self, self._modify_value_before_insert(item, len(self)))

    def extend(self, iterable):
        for v in iterable:
            self._additem(v)
        self._update_elems()
        return list.extend(self, [self._modify_value_before_insert(v, len(self) + i) for i, v in enumerate(iterable)])

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

    def _modify_value_before_insert(self, value, position):
        """Give subclasses an opportunity to alter the data before inserting. This function is called for each value
        being inserted into the list.
        """
        return value


class TagXmlList(XmlList, Nestable):
    """Abstract class that creates elements of the list based on the provided tag."""
    def __init__(self, instance, tag, nesting=None, *args, **kwargs):
        self.tag = tag
        Nestable.__init__(self, nesting)
        XmlList.__init__(self, instance=instance, *args, **kwargs)

    def _update_elems(self):
        self._elems = self.rootnode(self.instance).findall(self.tag)


class XmlTextList(TagXmlList):
    """This is a list of strings linked to an element's text.
    The list can only contain strings but can be passed any type, which will be converted to strings"""

    def _create_new_node(self, value):
        node = ElementTree.Element(self.tag)
        node.text = str(value)
        return node

    def _parse_element(self, element, lims, **kwargs):
        list.append(self, element.text)


class XmlAttributeList(TagXmlList):
    """This is a list of dicts linked to an element's attributes.
    The list can only contain and be provided with dict elements.
    The internal dicts are XmlElementAttributeDict objects which can be modified directly to modify the XML"""

    def _create_new_node(self, value):
        if not isinstance(value, dict):
            raise TypeError('You need to provide a dict not ' + type(value))
        node = ElementTree.Element(self.tag)
        for k, v in value.items():
            node.attrib[k] = v
        return node

    def _parse_element(self, element, lims, position, **kwargs):
        d = XmlElementAttributeDict(self.instance, tag=self.tag, nesting=self.rootkeys, position=position)
        list.append(self, d)

    def _modify_value_before_insert(self, value, position):
        return XmlElementAttributeDict(self.instance, tag=self.tag, nesting=self.rootkeys, position=position)


class XmlActionList(TagXmlList):
    def __init__(self, instance, *args, **kwargs):
        TagXmlList.__init__(self, instance, tag='next-action', nesting=['next-actions'], *args, **kwargs)

    def _create_new_node(self, value):
        if not isinstance(value, dict):
            raise TypeError('You need to provide a dict not ' + type(value))
        node = ElementTree.Element(self.tag)
        for k, v in value.items():
            if k in ['artifact', 'step', 'rework-step']:
                k = k + '-uri'
                v = v.uri
            node.attrib[k] = v
        return node

    def _parse_element(self, element, lims, position, **kwargs):
        d = XmlAction(self.instance, tag=self.tag, nesting=self.rootkeys, position=position)
        list.append(self, d)

    def _modify_value_before_insert(self, value, position):
        return XmlAction(self.instance, tag=self.tag, nesting=self.rootkeys, position=position)


class XmlReagentLabelList(XmlAttributeList):
    """List of reagent labels."""

    def __init__(self, instance, nesting=None, *args, **kwargs):
        XmlAttributeList.__init__(self, instance, tag='reagent-label', nesting=nesting, *args, **kwargs)

    def _create_new_node(self, value):
        return XmlAttributeList._create_new_node(self, {'name': value})

    def _parse_element(self, element, lims, **kwargs):
        list.append(self, element.attrib['name'])

    def _modify_value_before_insert(self, value, position):
        return value


class EntityList(TagXmlList):
    """List of entities. The list can only contain entities of the provided class (klass)"""

    def __init__(self, instance, tag, klass, nesting=None, *args, **kwargs):
        self.klass = klass
        TagXmlList.__init__(self, instance, tag, nesting=nesting, *args, **kwargs)

    def _create_new_node(self, value):
        if not isinstance(value, self.klass):
            raise TypeError('You need to provide an %s not %s' % (self.klass, type(value)))
        node = ElementTree.Element(self.tag)
        node.attrib['uri'] = value.uri
        return node

    def _parse_element(self, element, lims, **kwargs):
        list.append(self, self.klass(lims, uri=element.attrib['uri']))


class XmlInputOutputMapList(TagXmlList):
    """An instance attribute yielding a list of tuples (input, output)
    where each item is a dictionary, representing the input/output
    maps of a Process instance.
    """

    def __init__(self, instance, *args, **kwargs):
        TagXmlList.__init__(self, instance, 'input-output-map', *args, **kwargs)

    def _parse_element(self, element, lims, **kwargs):
        input_element = self._get_dict(lims, element.find('input'))
        output_element = self._get_dict(lims, element.find('output'))
        list.append(self, (input_element, output_element))

    def _get_dict(self, lims, node):
        from pyclarity_lims.entities import Artifact, Process
        if node is None:
            return None
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
        node = node.find('parent-process')
        if node is not None:
            result['parent-process'] = Process(lims, node.attrib['uri'])
        return result

    def _set_dict(self, element, value_dict):
        for key in ['limsid', 'output-type', 'output-generation-type']:
            if key in value_dict:
                element.attrib[key] = value_dict[key]
        for key in ['uri', 'post-process-uri']:
            if key in value_dict:
                element.attrib[key] = value_dict[key].uri
        if 'parent-process' in value_dict:
            node = ElementTree.SubElement(element, 'parent-process')
            node.attrib['uri'] = value_dict['parent-process'].uri

    def _create_new_node(self, value ):
        if not isinstance(value, tuple):
            raise TypeError('You need to provide a tuple not %s' % (type(value)))
        if len(value) != 2:
            raise TypeError('You need to provide a tuple with 2 values, found %s' % len(value))
        input_dict, output_dict = value
        node = ElementTree.Element(self.tag)
        input_element = ElementTree.SubElement(node, 'input')
        output_element = ElementTree.SubElement(node, 'output')
        self._set_dict(input_element, input_dict)
        self._set_dict(output_element, output_dict)
        return node


class OutputPlacementList(TagXmlList):
    """This is a list of output placements as found in the StepPlacement. The list contains tuples organised as follows:
    (A, (B, C)) where
     A is an artifact
     B is a container
     C is a string specifying the location such as "1:1"
    """

    def __init__(self, instance, *args, **kwargs):
        TagXmlList.__init__(self, instance, tag='output-placement', nesting=['output-placements'], *args, **kwargs)

    def _create_new_node(self, value):
        if not isinstance(value, tuple):
            raise TypeError('You need to provide a tuple not %s' % (type(value)))
        art, location = value
        container, position = location
        node = ElementTree.Element(self.tag)
        node.attrib['uri'] = art.uri
        elem = ElementTree.SubElement(node, 'location')
        ElementTree.SubElement(elem, 'container', uri=container.uri, limsid=container.id)
        v = ElementTree.SubElement(elem, 'value')
        v.text = position
        return node

    def _parse_element(self, element, lims, **kwargs):
        from pyclarity_lims.entities import Artifact, Container
        input = Artifact(lims, uri=element.attrib['uri'])
        loc = element.find('location')
        location = (None, None)
        if loc:
            location = (
                Container(lims, uri=loc.find('container').attrib['uri']),
                loc.find('value').text
            )
        list.append(self, (input, location))


class ExternalidList(XmlList):
    def _update_elems(self):
        self._elems = self.rootnode(self.instance).findall(nsmap('ri:externalid'))

    def _create_new_node(self, value):
        if not isinstance(value, tuple):
            raise TypeError('You need to provide a tuple not ' + type(value))
        node = ElementTree.Element(nsmap('ri:externalid'))
        id, uri = value
        node.attrib['id'] = id
        node.attrib['uri'] = uri
        return node

    def _parse_element(self, element, **kwargs):
        list.append(self, (element.attrib.get('id'), element.attrib.get('uri')))


class QueuedArtifactList(TagXmlList):
    """This is a list of Artifacts associated with the time they spent in the queue and their location on a plate.
    The list contains tuples organised as follows:
        (A, B, (C, D)) where
         A is an artifact
         B is a datetime object,
         C is a container
         D is a string specifying the location such as "1:1"
        """

    def __init__(self, instance, *args, **kwargs):
        TagXmlList.__init__(self, instance, tag='artifact', nesting=['artifacts'], *args, **kwargs)

    def _parse_element(self, element, lims, **kwargs):
        from pyclarity_lims.entities import Artifact, Container
        input_art = Artifact(lims, uri=element.attrib['uri'])
        loc = element.find('location')
        location = (None, None)
        if loc:
            location = (
                Container(lims, uri=loc.find('container').attrib['uri']),
                loc.find('value').text
            )
        qt = element.find('queue-time')
        queue_date = None
        if qt is not None:
            h, s, t = qt.text.rpartition(':')
            qt = h + t
            microsec = ''
            if '.' in qt:
                microsec = '.%f'
            date_format = '%Y-%m-%dT%H:%M:%S' + microsec
            try:
                queue_date = datetime.datetime.strptime(qt, date_format + '%z')
            except ValueError:
                # support for python 2.7 ignore time zone
                # use python 3 for timezone support
                if '+' in qt:
                    qt = qt.split('+')[0]
                else:
                    qt_array = qt.split('-')
                    qt = qt_array[0] + "-" + qt_array[1] + "-" + qt_array[2]
                queue_date = datetime.datetime.strptime(qt, date_format)
        list.append(self, (input_art, queue_date, location))

    def _update_elems(self):
        root = self.instance.root
        self._elems = []
        while root:
            self._elems += self.rootnode_from_root(root).findall(self.tag)
            if root.find('next-page') is not None:
                root = self.instance.lims.get(root.find('next-page').attrib.get('uri'))
            else:
                root = None


# Descriptors: This section contains the objects that can be used in entities
class BaseDescriptor(XmlElement):
    """Abstract base descriptor for an instance attribute."""

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
            return self.rootnode(instance).find(self.tag)
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


class StringAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        instance.get()
        return instance.root.attrib[self.tag]

    def __set__(self, instance, value):
        instance.get()
        instance.root.attrib[self.tag] = value


class EntityDescriptor(TagDescriptor):
    """An instance attribute referencing another entity instance."""

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
        # if value._TAG in ['project', 'sample', 'artifact', 'container']:
        #     node.attrib['limsid'] = value.id


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
        from pyclarity_lims.entities import Container
        instance.get()
        node = self.rootnode(instance).find(self.tag)
        if node:
            uri = node.find('container').attrib['uri']
            return Container(instance.lims, uri=uri), node.find('value').text
        else:
            return None


class MutableDescriptor(BaseDescriptor):
    """An instance attribute yielding a list or dict of mutable objects
    represented by XML elements.
    """

    def __init__(self, muttableklass, **kwargs):
        self.muttableklass = muttableklass
        self.kwargs = kwargs

    def __get__(self, instance, cls):
        instance.get()
        return self.muttableklass(instance=instance, **self.kwargs)

    def __set__(self, instance, value):
        instance.get()
        muttable = self.muttableklass(instance=instance, **self.kwargs)
        muttable.clear()
        if issubclass(self.muttableklass, list):
            return muttable.extend(value)
        elif issubclass(self.muttableklass, dict):
            for k in value:
                muttable[k] = value[k]


class UdfDictionaryDescriptor(MutableDescriptor):
    """An instance attribute containing a dictionary of UDF values
    represented by multiple XML elements.
    """
    def __init__(self, **kwargs):
        MutableDescriptor.__init__(self, UdfDictionary, udt=False, **kwargs)


class UdtDictionaryDescriptor(MutableDescriptor):
    """An instance attribute containing a dictionary of UDF values
    in a UDT represented by multiple XML elements.
    """

    def __init__(self, **kwargs):
        MutableDescriptor.__init__(self, UdfDictionary, udt=True, **kwargs)


class PlacementDictionaryDescriptor(MutableDescriptor):
    """An instance attribute containing a dictionary of location
    keys and artifact values represented by multiple XML elements.
    """

    def __init__(self, **kwargs):
        MutableDescriptor.__init__(self, PlacementDictionary, **kwargs)


class EntityListDescriptor(MutableDescriptor):
    """An instance attribute yielding a list of entity instances
    represented by multiple XML elements.
    """

    def __init__(self, tag, klass, **kwargs):
        MutableDescriptor.__init__(self, EntityList, tag=tag, klass=klass, **kwargs)


class StringListDescriptor(MutableDescriptor):
    """An instance attribute containing a list of strings
    represented by multiple XML elements.
    """
    def __init__(self, tag, **kwargs):
        MutableDescriptor.__init__(self, XmlTextList, tag=tag, **kwargs)


class ReagentLabelList(MutableDescriptor):
    """An instance attribute yielding a list of reagent labels"""

    def __init__(self, **kwargs):
        MutableDescriptor.__init__(self, XmlReagentLabelList, **kwargs)


class AttributeListDescriptor(MutableDescriptor):
    """An instance yielding a list of dictionaries of attributes
       for a list of XML elements"""

    def __init__(self, tag, **kwargs):
        MutableDescriptor.__init__(self, XmlAttributeList, tag=tag, **kwargs)


class StringDictionaryDescriptor(MutableDescriptor):
    """An instance attribute containing a dictionary of string key/values
    represented by a hierarchical XML element.
    """

    def __init__(self, tag, **kwargs):
        MutableDescriptor.__init__(self, SubTagDictionary, tag=tag, **kwargs)


class InputOutputMapList(MutableDescriptor):
    """An instance attribute yielding a list of tuples (input, output)
    where each item is a dictionary, representing the input/output
    maps of a Process instance.
    """

    def __init__(self, **kwargs):
        MutableDescriptor.__init__(self, XmlInputOutputMapList, **kwargs)


class OutputPlacementListDescriptor(MutableDescriptor):
    """
    An instance attribute yielding a list of tuples (A, (B, C)) where:
    A is an artifact
    B is a container
    C is a string specifying the location such as "1:1"
    """

    def __init__(self, **kwargs):
        MutableDescriptor.__init__(self, OutputPlacementList, **kwargs)


class ExternalidListDescriptor(MutableDescriptor):
    """An instance attribute yielding a list of tuples (id, uri) for
    external identifiers represented by multiple XML elements.
    """

    def __init__(self, **kwargs):
        MutableDescriptor.__init__(self, ExternalidList, **kwargs)
