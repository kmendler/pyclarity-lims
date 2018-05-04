from sys import version_info
from io import BytesIO
from xml.etree import ElementTree

if version_info[0] == 2:
    from mock import Mock
else:
    from unittest.mock import Mock


class NamedMock(Mock):
    @property
    def name(self):
        return self.real_name


def elements_equal(e1, e2):
    if e1.tag != e2.tag:
        print('Tag: %s != %s' % (e1.tag, e2.tag))
        return False
    if e1.text and e2.text and e1.text.strip() != e2.text.strip():
        print('Text: %s != %s' % (e1.text.strip(), e2.text.strip()))
        return False
    if e1.tail and e2.tail and e1.tail.strip() != e2.tail.strip():
        print('Tail: %s != %s' % (e1.tail.strip(), e2.tail.strip()))
        return False
    if e1.attrib != e2.attrib:
        print('Attrib: %s != %s' % (e1.attrib, e2.attrib))
        return False
    if len(e1) != len(e2):
        print('length %s (%s) != length %s (%s) ' % (e1.tag, len(e1), e2.tag, len(e2)))
        return False
    return all(elements_equal(c1, c2) for c1, c2 in zip(sorted(e1, key=lambda x: x.tag), sorted(e2, key=lambda x: x.tag)))


def print_etree(etree):
    import sys
    outfile = BytesIO()
    ElementTree.ElementTree(etree).write(outfile, encoding='utf-8', xml_declaration=True)
    sys.stdout.buffer.write(outfile.getvalue())
