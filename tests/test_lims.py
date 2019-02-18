from unittest import TestCase
from xml.etree import ElementTree

from requests.exceptions import HTTPError

from pyclarity_lims.entities import Sample, Project, Container, Artifact
from pyclarity_lims.lims import Lims
from tests import elements_equal

try:
    callable(1)
except NameError:  # callable() doesn't exist in Python 3.0 and 3.1
    import collections
    callable = lambda obj: isinstance(obj, collections.Callable)

from sys import version_info
if version_info[0] == 2:
    from mock import patch, Mock
    import __builtin__ as builtins
else:
    from unittest.mock import patch, Mock
    import builtins


class TestLims(TestCase):
    url = 'http://testgenologics.com:4040'
    username = 'test'
    password = 'password'
    sample_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smp:samples xmlns:smp="http://pyclarity_lims.com/ri/sample">
    <sample uri="{url}/api/v2/samples/test_sample" limsid="test_id"/>
</smp:samples>
""".format(url=url)
    error_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<exc:exception xmlns:exc="http://pyclarity_lims.com/ri/exception">
    <message>Generic error message</message>
</exc:exception>"""
    error_no_msg_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<exc:exception xmlns:exc="http://pyclarity_lims.com/ri/exception">
</exc:exception>"""

    def test_get_uri(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        assert lims.get_uri('artifacts', sample_name='test_sample') == '{url}/api/v2/artifacts?sample_name=test_sample'.format(url=self.url)

    def test_parse_response(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        r = Mock(content=self.sample_xml, status_code=200)
        pr = lims.parse_response(r)
        assert pr is not None
        assert callable(pr.find)
        assert hasattr(pr.attrib, '__getitem__')

        r = Mock(content=self.error_xml, status_code=400)
        self.assertRaises(HTTPError, lims.parse_response, r)

        r = Mock(content=self.error_no_msg_xml, status_code=400)
        self.assertRaises(HTTPError, lims.parse_response, r)

    @patch('requests.Session.get', return_value=Mock(content=sample_xml, status_code=200))
    def test_get(self, mocked_instance):
        lims = Lims(self.url, username=self.username, password=self.password)
        r = lims.get('{url}/api/v2/artifacts?sample_name=test_sample'.format(url=self.url))
        assert r is not None
        assert callable(r.find)
        assert hasattr(r.attrib, '__getitem__')
        assert mocked_instance.call_count == 1
        mocked_instance.assert_called_with(
            'http://testgenologics.com:4040/api/v2/artifacts?sample_name=test_sample',
            timeout=16, headers={'accept': 'application/xml'}, params={}, auth=('test', 'password')
        )

    def test_put(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        uri = '{url}/api/v2/samples/test_sample'.format(url=self.url)
        with patch('requests.put', return_value=Mock(content=self.sample_xml, status_code=200)) as mocked_put:
            lims.put(uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1
        with patch('requests.put', return_value=Mock(content=self.error_xml, status_code=400)) as mocked_put:
            self.assertRaises(HTTPError, lims.put, uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1

    def test_post(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        uri = '{url}/api/v2/samples'.format(url=self.url)
        with patch('requests.post', return_value=Mock(content=self.sample_xml, status_code=200)) as mocked_put:
            lims.post(uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1
        with patch('requests.post', return_value=Mock(content=self.error_xml, status_code=400)) as mocked_put:
            self.assertRaises(HTTPError, lims.post, uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1

    @patch('os.path.isfile', return_value=True)
    @patch.object(builtins, 'open')
    def test_upload_new_file(self, mocked_open, mocked_isfile):
        lims = Lims(self.url, username=self.username, password=self.password)
        xml_intro = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>"""
        file_start = """<file:file xmlns:file="http://pyclarity_lims.com/ri/file">"""
        file_start2 = """<file:file xmlns:file="http://pyclarity_lims.com/ri/file" uri="{url}/api/v2/files/40-3501" limsid="40-3501">"""
        attached = """    <attached-to>{url}/api/v2/samples/test_sample</attached-to>"""
        upload = """    <original-location>filename_to_upload</original-location>"""
        content_loc = """    <content-location>sftp://{url}/opt/gls/clarity/users/glsftp/clarity/samples/test_sample/test</content-location>"""
        file_end = """</file:file>"""
        glsstorage_xml = '\n'.join([xml_intro, file_start, attached, upload, content_loc, file_end]).format(url=self.url)
        file_post_xml = '\n'.join([xml_intro, file_start2, attached, upload, content_loc, file_end]).format(url=self.url)
        with patch('requests.post', side_effect=[Mock(content=glsstorage_xml, status_code=200),
                                                 Mock(content=file_post_xml, status_code=200),
                                                 Mock(content="", status_code=200)]):

            file = lims.upload_new_file(Mock(uri=self.url+"/api/v2/samples/test_sample"),
                                        'filename_to_upload')
            assert file.id == "40-3501"

        with patch('requests.post', side_effect=[Mock(content=self.error_xml, status_code=400)]):
            self.assertRaises(
                HTTPError, lims.upload_new_file, Mock(uri=self.url+"/api/v2/samples/test_sample"), 'filename_to_upload'
            )

    @patch('requests.post', return_value=Mock(content=sample_xml, status_code=200))
    def test_route_artifact(self, mocked_post):
        lims = Lims(self.url, username=self.username, password=self.password)
        artifact = Mock(uri=self.url+"/artifact/2")
        lims.route_artifacts(artifact_list=[artifact], workflow_uri=self.url+'/api/v2/configuration/workflows/1')
        assert mocked_post.call_count == 1

    def test_tostring(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        from xml.etree import ElementTree as ET
        a = ET.Element('a')
        b = ET.SubElement(a, 'b')
        c = ET.SubElement(a, 'c')
        d = ET.SubElement(c, 'd')
        etree = ET.ElementTree(a)
        expected_string = b"""<?xml version='1.0' encoding='utf-8'?>
<a><b /><c><d /></c></a>"""
        string = lims.tostring(etree)
        assert string == expected_string

    def test_get_file_contents(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        lims.validate_response = Mock()
        lims.request_session = Mock(get=Mock(return_value=Mock(encoding=None, text='some data\r\n')))
        exp_url = self.url + '/api/v2/files/an_id/download'

        assert lims.get_file_contents(uri=self.url + '/api/v2/files/an_id') == 'some data\r\n'
        assert lims.request_session.get.return_value.encoding is None
        lims.request_session.get.assert_called_with(exp_url, auth=(self.username, self.password), timeout=16)

        assert lims.get_file_contents(id='an_id', encoding='utf-16', crlf=True) == 'some data\n'
        assert lims.request_session.get.return_value.encoding == 'utf-16'
        lims.request_session.get.assert_called_with(exp_url, auth=(self.username, self.password), timeout=16)

        lims.request_session = Mock(get=Mock(return_value=Mock(text='some data\n', content=b'some binary data')))
        assert lims.get_file_contents(uri=self.url + '/api/v2/files/an_id', binary=True) == b'some binary data'

    def test_get_instances(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        sample_xml_template = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <smp:samples xmlns:smp="http://pyclarity_lims.com/ri/sample">
            <sample uri="{url}/api/v2/samples/{s1}" limsid="{s1}"/>
            <sample uri="{url}/api/v2/samples/{s2}" limsid="{s2}"/>
            {next_page}
        </smp:samples>
        """
        sample_xml1 = sample_xml_template.format(
            s1='sample1', s2='sample2',
            url=self.url,
            next_page='<next-page uri="{url}/api/v2/samples?start-index=3"/>'.format(url=self.url)
        )
        sample_xml2 = sample_xml_template.format(
            s1='sample3', s2='sample4',
            url=self.url,
            next_page='<next-page uri="{url}/api/v2/samples?start-index=5"/>'.format(url=self.url)
        )
        sample_xml3 = sample_xml_template.format(
            s1='sample5', s2='sample6',
            url=self.url,
            next_page=''
        )
        get_returns = [
            Mock(content=sample_xml1, status_code=200),
            Mock(content=sample_xml2, status_code=200),
            Mock(content=sample_xml3, status_code=200)
        ]

        with patch('requests.Session.get', side_effect=get_returns) as mget:
            samples = lims._get_instances(Sample, nb_pages=2, params={'projectname': 'p1'})
            assert len(samples) == 4
            assert mget.call_count == 2
            mget.assert_any_call(
                'http://testgenologics.com:4040/api/v2/samples',
                auth=('test', 'password'),
                headers={'accept': 'application/xml'},
                params={'projectname': 'p1'},
                timeout=16
            )
            mget.assert_called_with(
                'http://testgenologics.com:4040/api/v2/samples?start-index=3',
                auth=('test', 'password'),
                headers={'accept': 'application/xml'},
                params={'projectname': 'p1'},
                timeout=16
            )

        with patch('requests.Session.get', side_effect=get_returns) as mget:
            samples = lims._get_instances(Sample, nb_pages=0)
            assert len(samples) == 6
            assert mget.call_count == 3

        with patch('requests.Session.get', side_effect=get_returns) as mget:
            samples = lims._get_instances(Sample, nb_pages=-1)
            assert len(samples) == 6
            assert mget.call_count == 3

    def test_get_batch(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        arts = [Artifact(lims, id='a1'), Artifact(lims, id='a2')]
        artifact_list = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <art:details xmlns:art="http://genologics.com/ri/artifact">
          <art:artifact limsid="a1" uri="{url}/artifacts/a1">
            <name>art1</name>
            <type>type1</type>
          </art:artifact>
          <art:artifact limsid="a2" uri="{url}/artifacts/a2">
            <name>art2</name>
            <type>type2</type>
          </art:artifact>
        </art:details>
        '''
        with patch('requests.post', return_value=Mock(content=artifact_list, status_code=200)) as mocked_post:
            arts = lims.get_batch(arts)
            assert type(arts) == list
            assert arts[0].name == 'art1'
            assert arts[1].name == 'art2'
            mocked_post.assert_called_once_with(
                'http://testgenologics.com:4040/api/v2/artifacts/batch/retrieve',
                auth=('test', 'password'),
                data=b'<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<ri:links xmlns:ri="http://genologics.com/ri"><link rel="artifacts" uri="http://testgenologics.com:4040/api/v2/artifacts/a1" /><link rel="artifacts" uri="http://testgenologics.com:4040/api/v2/artifacts/a2" /></ri:links>',
                headers={'content-type': 'application/xml', 'accept': 'application/xml'}, params={})

    def test_create_batch(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        p = Project(lims, uri='project')
        c = Container(lims, uri='container')
        sample_links = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <ri:links xmlns:ri="http://genologics.com/ri">
            <link rel="samples" uri="sample1"/>
            <link rel="samples" uri="sample2"/>
            <link rel="samples" uri="sample3"/>
            <link rel="samples" uri="sample4"/>
            <link rel="samples" uri="sample5"/>
        </ri:links>"""
        with patch('requests.post', return_value=Mock(content=sample_links, status_code=200)) as mocked_post:
            samples = lims.create_batch(
                Sample,
                [
                    {'project': p, 'container': c, 'position': '1:1', 'name': 's1', 'udf': {'test1': 'test1value1'}},
                    {'project': p, 'container': c, 'position': '1:2', 'name': 's2', 'udf': {'test1': 'test1value2'}},
                    {'project': p, 'container': c, 'position': '1:3', 'name': 's3', 'udf': {'test1': 'test1value3'}},
                    {'project': p, 'container': c, 'position': '1:4', 'name': 's4', 'udf': {'test1': 'test1value4'}},
                    {'project': p, 'container': c, 'position': '1:5', 'name': 's5', 'udf': {'test1': 'test1value5'}},
                ]
            )
            assert [s.uri for s in samples] == ['sample1', 'sample2', 'sample3', 'sample4', 'sample5']
            assert mocked_post.call_args[0][0] == 'http://testgenologics.com:4040/api/v2/samples/batch/create'
            et = ElementTree.fromstring(mocked_post.call_args[1]['data'])
            children = et.getchildren()
            for i in range(5):
                assert elements_equal(children[i], samples[i].root)


