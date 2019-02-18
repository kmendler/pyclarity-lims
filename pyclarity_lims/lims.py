import os
import re
from io import BytesIO
import requests

# python 2.7, 3+ compatibility
from sys import version_info

if version_info[0] == 2:
    from urlparse import urljoin
    from urllib import urlencode
else:
    from urllib.parse import urljoin
    from urllib.parse import urlencode

from .entities import *

__all__ = ['Lab', 'Researcher', 'Project', 'Sample', 'Containertype', 'Container', 'Processtype', 'Process',
           'Artifact', 'Lims']

# Python 2.6 support work-arounds
# - Exception ElementTree.ParseError does not exist
# - ElementTree.ElementTree.write does not take arg. xml_declaration
if version_info[:2] < (2, 7):
    from xml.parsers import expat
    ElementTree.ParseError = expat.ExpatError
    p26_write = ElementTree.ElementTree.write

    def write_with_xml_declaration(self, file, encoding, xml_declaration):
        assert xml_declaration is True  # Support our use case only
        file.write("<?xml version='1.0' encoding='utf-8'?>\n")
        p26_write(self, file, encoding=encoding)
    ElementTree.ElementTree.write = write_with_xml_declaration

TIMEOUT = 16


class Lims(object):
    """
    LIMS interface through which all searches can be performed and :py:class:`Entity <pyclarity_lims.entities.Entity>` instances are retrieved.

    :param baseuri: Base URI for the GenoLogics server, excluding the 'api' or version parts!
    :param username: The account name of the user to login as.
    :param password: The password for the user account to login as.
    :param version: The optional LIMS API version, by default 'v2'

    Example: ::

        Lims('https://claritylims.example.com', 'username' , 'Pa55w0rd')

    """

    VERSION = 'v2'

    def __init__(self, baseuri, username, password, version=VERSION):
        self.baseuri = baseuri.rstrip('/') + '/'
        self.username = username
        self.password = password
        self.VERSION = version
        self.cache = dict()
        # For optimization purposes, enables requests to persist connections
        self.request_session = requests.Session()
        # The connection pool has a default size of 10
        self.adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
        self.request_session.mount('http://', self.adapter)

    def get_uri(self, *segments, **query):
        """
        Return the full URI given the path segments and optional query.

        :param segments: arguments creating the uri
        :param query: kwargs creating the query
        """
        segments = ['api', self.VERSION] + list(segments)
        url = urljoin(self.baseuri, '/'.join(segments))
        if query:
            url += '?' + urlencode(query)
        return url

    def get(self, uri, params=dict()):
        """
        GET data from the URI. It checks the status and return the text of response as an ElementTree.

        :param uri: the uri to query
        :param params: dict containing the query parameters
        :return: the text of the response as an ElementTree
        """
        try:
            r = self.request_session.get(uri, params=params,
                                         auth=(self.username, self.password),
                                         headers=dict(accept='application/xml'),
                                         timeout=TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            raise type(e)("{0}, Error trying to reach {1}".format(e.message, uri))
        else:
            return self.parse_response(r)

    def get_file_contents(self, id=None, uri=None, encoding=None, crlf=False, binary=False):
        r"""
        Download and returns the contents of the file of <ID> or <uri>.

        :param id: the id of the file to retrieve.
        :param uri: the uri of the file to retrieve.
        :param encoding: When retrieve text file, this option can specify the encoding of the file.
        :param crlf: When set to True the text file will be replace \\r\\n by \\n.
        :param binary: When set to True the file content is returned as a binary stream.
        :return: The file content in the format specify by the parameters.
        """
        if id:
            url = self.get_uri('files', id, 'download')
        elif uri:
            url = uri.rstrip('/') + '/download'
        else:
            raise ValueError('id or uri required')

        r = self.request_session.get(url, auth=(self.username, self.password), timeout=TIMEOUT)
        self.validate_response(r)
        if binary:
            return r.content
        if encoding:
            r.encoding = encoding

        return r.text.replace('\r\n', '\n') if crlf else r.text

    def upload_new_file(self, entity, file_to_upload):
        """Upload a file and attach it to the provided entity."""
        file_to_upload = os.path.abspath(file_to_upload)
        if not os.path.isfile(file_to_upload):
            raise IOError("{} not found".format(file_to_upload))

        # Request the storage space on glsstorage
        # Create the xml to describe the file
        root = ElementTree.Element(nsmap('file:file'))
        s = ElementTree.SubElement(root, 'attached-to')
        s.text = entity.uri
        s = ElementTree.SubElement(root, 'original-location')
        s.text = file_to_upload
        root = self.post(
            uri=self.get_uri('glsstorage'),
            data=self.tostring(ElementTree.ElementTree(root))
        )

        # Create the file object
        root = self.post(
            uri=self.get_uri('files'),
            data=self.tostring(ElementTree.ElementTree(root))
        )
        file = File(self, uri=root.attrib['uri'])

        # Actually upload the file
        uri = self.get_uri('files', file.id, 'upload')
        r = requests.post(uri, files={'file': (file_to_upload, open(file_to_upload, 'rb'))},
                          auth=(self.username, self.password))
        self.validate_response(r)
        return file

    def put(self, uri, data, params=dict()):
        """
        PUT the serialized XML to the given URI.
        Return the response XML as an ElementTree.
        """
        r = requests.put(uri, data=data, params=params,
                         auth=(self.username, self.password),
                         headers={'content-type': 'application/xml',
                                  'accept': 'application/xml'})
        return self.parse_response(r)

    def post(self, uri, data, params=dict()):
        """
        POST the serialized XML to the given URI.
        Return the response XML as an ElementTree.
        """
        r = requests.post(uri, data=data, params=params,
                          auth=(self.username, self.password),
                          headers={'content-type': 'application/xml',
                                   'accept': 'application/xml'})
        return self.parse_response(r, accept_status_codes=[200, 201, 202])

    def check_version(self):
        """
        Raise ValueError if the version for this interface
        does not match any of the versions given for the API.
        """
        uri = urljoin(self.baseuri, 'api')
        r = requests.get(uri, auth=(self.username, self.password))
        root = self.parse_response(r)
        tag = nsmap('ver:versions')
        assert tag == root.tag
        for node in root.findall('version'):
            if node.attrib['major'] == self.VERSION:
                return
        raise ValueError('version mismatch')

    def validate_response(self, response, accept_status_codes=[200]):
        """Parse the XML returned in the response.
        Raise an HTTP error if the response status is not one of the
        specified accepted status codes.
        """
        if response.status_code not in accept_status_codes:
            try:
                root = ElementTree.fromstring(response.content)
                node = root.find('message')
                if node is None:
                    response.raise_for_status()
                    message = "%s" % response.status_code
                else:
                    message = "%s: %s" % (response.status_code, node.text)
                node = root.find('suggested-actions')
                if node is not None:
                    message += ' ' + node.text
            except ElementTree.ParseError:  # some error messages might not follow the xml standard
                message = response.content
            raise requests.exceptions.HTTPError(message)
        return True

    def parse_response(self, response, accept_status_codes=[200]):
        """Parse the XML returned in the response.
        Raise an HTTP error if the response status is not 200.
        """
        self.validate_response(response, accept_status_codes)
        root = ElementTree.fromstring(response.content)
        return root

    def get_udfs(self, name=None, attach_to_name=None, attach_to_category=None, start_index=None, nb_pages=-1,
                 add_info=False):
        """Get a list of udfs, filtered by keyword arguments.

        :param name: name of udf
        :param attach_to_name: item in the system, to wich the udf is attached, such as
            Sample, Project, Container, or the name of a process.
        :param attach_to_category: If 'attach_to_name' is the name of a process, such as 'CaliperGX QC (DNA)',
                                   then you need to set attach_to_category='ProcessType'. Must not be provided otherwise.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.
        """
        params = self._get_params(name=name,
                                  attach_to_name=attach_to_name,
                                  attach_to_category=attach_to_category,
                                  start_index=start_index)
        return self._get_instances(Udfconfig, add_info=add_info, nb_pages=nb_pages, params=params)

    def get_reagent_types(self, name=None, start_index=None, nb_pages=-1, add_info=False):
        """
        Get a list of reagent types, filtered by keyword arguments.

        :param name: Reagent type name, or list of names.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                        the second is a dict of additional information provided in the query.

        """
        params = self._get_params(name=name, start_index=start_index)
        return self._get_instances(ReagentType, nb_pages=nb_pages, add_info=add_info, params=params)

    def get_labs(self, name=None, last_modified=None,
                 udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1, add_info=False):
        """Get a list of labs, filtered by keyword arguments.

        :param name: Lab name, or list of names.
        :param last_modified: Since the given ISO format datetime.
        :param udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        :param udtname: UDT name, or list of names.
        :param udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
                    and a string or list of strings as value.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.
        """
        params = self._get_params(name=name,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Lab, add_info=add_info, nb_pages=nb_pages, params=params)

    def get_researchers(self, firstname=None, lastname=None, username=None,
                        last_modified=None,
                        udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1,
                        add_info=False):
        """Get a list of researchers, filtered by keyword arguments.

        :param firstname: Researcher first name, or list of names.
        :param lastname: Researcher last name, or list of names.
        :param username: Researcher account name, or list of names.
        :param last_modified: Since the given ISO format datetime.
        :param udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        :param udtname: UDT name, or list of names.
        :param udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
                    and a string or list of strings as value.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.

        """
        params = self._get_params(firstname=firstname,
                                  lastname=lastname,
                                  username=username,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Researcher, add_info=add_info, nb_pages=nb_pages, params=params)

    def get_projects(self, name=None, open_date=None, last_modified=None,
                     udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1,
                     add_info=False):
        """Get a list of projects, filtered by keyword arguments.

        :param name: Project name, or list of names.
        :param open_date: Since the given ISO format date.
        :param last_modified: Since the given ISO format datetime.
        :param udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        :param udtname: UDT name, or list of names.
        :param udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
                    and a string or list of strings as value.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.

        """
        params = self._get_params(name=name,
                                  open_date=open_date,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Project, add_info=add_info, nb_pages=nb_pages, params=params)

    def get_sample_number(self, name=None, projectname=None, projectlimsid=None,
                          udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1):
        """
        Gets the number of samples matching the query without fetching every
        sample, so it should be faster than len(get_samples())
        """
        # TODO: I doubt that this make any difference in terms of speed since the only thing it save is the Sample
        # construction. We should test and a replace with len(get_samples())
        params = self._get_params(name=name,
                                  projectname=projectname,
                                  projectlimsid=projectlimsid,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        root = self.get(self.get_uri(Sample._URI), params=params)
        total = 0
        while params.get('start-index') is None:  # Loop over all pages.
            total += len(root.findall("sample"))
            node = root.find('next-page')
            if node is None: break
            root = self.get(node.attrib['uri'], params=params)
        return total

    def get_samples(self, name=None, projectname=None, projectlimsid=None,
                    udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1):
        """Get a list of samples, filtered by keyword arguments.

        :param name: Sample name, or list of names.
        :param projectlimsid: Samples for the project of the given LIMS id.
        :param projectname: Samples for the project of the name.
        :param udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        :param udtname: UDT name, or list of names.
        :param udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
                    and a string or list of strings as value.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        """
        params = self._get_params(name=name,
                                  projectname=projectname,
                                  projectlimsid=projectlimsid,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Sample, nb_pages=nb_pages, params=params)

    def get_artifacts(self, name=None, type=None, process_type=None,
                      artifact_flag_name=None, working_flag=None, qc_flag=None,
                      sample_name=None, samplelimsid=None, artifactgroup=None, containername=None,
                      containerlimsid=None, reagent_label=None,
                      udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1,
                      resolve=False):
        """Get a list of artifacts, filtered by keyword arguments.

        :param name: Artifact name, or list of names.
        :param type: Artifact type, or list of types.
        :param process_type: Produced by the process type, or list of types.
        :param artifact_flag_name: Tagged with the genealogy flag, or list of flags.
        :param working_flag: Having the given working flag; boolean.
        :param qc_flag: Having the given QC flag: UNKNOWN, PASSED, FAILED.
        :param sample_name: Related to the given sample name.
        :param samplelimsid: Related to the given sample id.
        :param artifactgroup: Belonging to the artifact group (experiment in client).
        :param containername: Residing in given container, by name, or list.
        :param containerlimsid: Residing in given container, by LIMS id, or list.
        :param reagent_label: having attached reagent labels.
        :param udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        :param udtname: UDT name, or list of names.
        :param udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
                    and a string or list of strings as value.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param resolve: Send a batch query to the lims to get the content of all artifacts retrieved
        """
        params = self._get_params(name=name,
                                  type=type,
                                  process_type=process_type,
                                  artifact_flag_name=artifact_flag_name,
                                  working_flag=working_flag,
                                  qc_flag=qc_flag,
                                  sample_name=sample_name,
                                  samplelimsid=samplelimsid,
                                  artifactgroup=artifactgroup,
                                  containername=containername,
                                  containerlimsid=containerlimsid,
                                  reagent_label=reagent_label,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        if resolve:
            return self.get_batch(self._get_instances(Artifact, nb_pages=nb_pages, params=params))
        else:
            return self._get_instances(Artifact, nb_pages=nb_pages, params=params)

    def get_containers(self, name=None, type=None,
                       state=None, last_modified=None,
                       udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1,
                       add_info=False):
        """Get a list of containers, filtered by keyword arguments.

        :param name: Containers name, or list of names.
        :param type: Container type, or list of types.
        :param state: Container state: Empty, Populated, Discarded, Reagent-Only.
        :param last_modified: Since the given ISO format datetime.
        :param udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        :param udtname: UDT name, or list of names.
        :param udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
                    and a string or list of strings as value.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.
        """
        params = self._get_params(name=name,
                                  type=type,
                                  state=state,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Container, add_info=add_info, nb_pages=nb_pages, params=params)

    def get_container_types(self, name=None, start_index=None, nb_pages=-1, add_info=False):
        """Get a list of container types, filtered by keyword arguments.

        :param name: name of the container type or list of names.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.
        """
        params = self._get_params(name=name, start_index=start_index)
        return self._get_instances(Containertype, add_info=add_info, nb_pages=nb_pages, params=params)

    def get_processes(self, last_modified=None, type=None,
                      inputartifactlimsid=None,
                      techfirstname=None, techlastname=None, projectname=None,
                      udf=dict(), udtname=None, udt=dict(), start_index=None, nb_pages=-1):
        """Get a list of processes, filtered by keyword arguments.

        :param last_modified: Since the given ISO format datetime.
        :param type: Process type, or list of types.
        :param inputartifactlimsid: Input artifact LIMS id, or list of.
        :param udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        :param udtname: UDT name, or list of names.
        :param udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
                    and a string or list of strings as value.
        :param techfirstname: First name of researcher, or list of.
        :param techlastname: Last name of researcher, or list of.
        :param projectname: Name of project, or list of.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        """
        params = self._get_params(last_modified=last_modified,
                                  type=type,
                                  inputartifactlimsid=inputartifactlimsid,
                                  techfirstname=techfirstname,
                                  techlastname=techlastname,
                                  projectname=projectname,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Process, nb_pages=nb_pages, params=params)

    def get_workflows(self, name=None, add_info=False):
        """
        Get a list of existing workflows on the system.

        :param name: The name of the workflow you're looking for
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.

        """
        params = self._get_params(name=name)
        return self._get_instances(Workflow, add_info=add_info, params=params)

    def get_process_types(self, displayname=None, add_info=False):
        """
        Get a list of process types with the specified name.

        :param displayname: The name the process type
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.

        """
        params = self._get_params(displayname=displayname)
        return self._get_instances(Processtype, add_info=add_info, params=params)

    def get_protocols(self, name=None, add_info=False):
        """
        Get a list of existing protocols on the system.

        :param name: The name the protocol
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.

        """
        params = self._get_params(name=name)
        return self._get_instances(Protocol, add_info=add_info, params=params)

    def get_reagent_kits(self, name=None, start_index=None, nb_pages=-1, add_info=False):
        """Get a list of reagent kits, filtered by keyword arguments.

        :param name: reagent kit  name, or list of names.
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        :param add_info: Change the return type to a tuple where the first element is normal return and
                         the second is a dict of additional information provided in the query.

        """
        params = self._get_params(name=name,
                                  start_index=start_index)
        return self._get_instances(ReagentKit, add_info=add_info, nb_pages=nb_pages, params=params)

    def get_reagent_lots(self, name=None, kitname=None, number=None,
                         start_index=None, nb_pages=-1):
        """Get a list of reagent lots, filtered by keyword arguments.

        :param name: reagent kit  name, or list of names.
        :param kitname: name of the kit this lots belong to
        :param number: lot number or list of lot number
        :param start_index: first element to retrieve; start at first element if None.
        :param nb_pages: number of page to iterate over. The page size is 500 by default unless configured otherwise
                        in your LIMS. 0 or negative numbers returns all pages.
        """
        params = self._get_params(name=name, kitname=kitname, number=number,
                                  start_index=start_index)
        return self._get_instances(ReagentLot, nb_pages=nb_pages, params=params)

    def _get_params(self, **kwargs):
        """Convert keyword arguments to a kwargs dictionary."""
        result = dict()
        for key, value in kwargs.items():
            if value is None:
                continue
            result[key.replace('_', '-')] = value
        return result

    def _get_params_udf(self, udf=dict(), udtname=None, udt=dict()):
        """Convert UDF-ish arguments to a params dictionary."""
        result = dict()
        for key, value in udf.items():
            result["udf.%s" % key] = value
        if udtname is not None:
            result['udt.name'] = udtname
        for key, value in udt.items():
            result["udt.%s" % key] = value
        return result

    def _get_instances(self, klass, add_info=None, nb_pages=-1, params=dict()):
        results = []
        additionnal_info_dicts = []
        tag = klass._TAG
        if tag is None:
            tag = klass.__name__.lower()
        root = self.get(self.get_uri(klass._URI), params=params)
        while root:  # Loop over all requested pages.
            nb_pages -= 1
            for node in root.findall(tag):
                results.append(klass(self, uri=node.attrib['uri']))
                info_dict = {}
                for attrib_key in node.attrib:
                    info_dict[attrib_key] = node.attrib[attrib_key]
                for subnode in node:
                    info_dict[subnode.tag] = subnode.text
                additionnal_info_dicts.append(info_dict)
            node = root.find('next-page')
            if node is None or nb_pages == 0:
                root = None
            else:
                root = self.get(node.attrib['uri'], params=params)
        if add_info:
            return results, additionnal_info_dicts
        else:
            return results

    def get_batch(self, instances, force=False):
        """Get the content of a set of instances using the efficient batch call.

        Returns the list of requested instances in arbitrary order, with duplicates removed
        (duplicates=entities occurring more than once in the instances argument).

        For Artifacts it is possible to have multiple instances with the same LIMSID but
        different URI, differing by a query parameter ?state=XX. If state is not
        given for an input URI, a state is added in the data returned by the batch
        API. In this case, the URI of the Entity object is not updated by this function
        (this is similar to how Entity.get() works). This may help with caching.

        The batch request API call collapses all requested Artifacts with different
        state into a single result with state equal to the state of the Artifact
        occurring at the last position in the list.

        :param instances: List of instances children of Entity
        :param force: optional argument to force the download of already cached instances
        """
        if not instances:
            return []
        root = ElementTree.Element(nsmap('ri:links'))
        needs_request = False
        instance_map = {}
        for instance in instances:
            instance_map[instance.id] = instance
            if force or instance.root is None:
                ElementTree.SubElement(root, 'link', dict(uri=instance.uri,
                                                          rel=instance.__class__._URI))
                needs_request = True

        if needs_request:
            uri = self.get_uri(instance.__class__._URI, 'batch/retrieve')
            data = self.tostring(ElementTree.ElementTree(root))
            root = self.post(uri, data)
            for node in root.getchildren():
                instance = instance_map[node.attrib['limsid']]
                instance.root = node
        return instances

    def put_batch(self, instances):
        """
        Update multiple instances using a single batch request.

        :param instances: List of instances children of Entity
        """

        if not instances:
            return

        root = None  # XML root element for batch request

        for instance in instances:
            if root is None:
                klass = instance.__class__
                # Tag is art:details, con:details, etc.
                example_root = instance.root
                ns_uri = re.match("{(.*)}.*", example_root.tag).group(1)
                root = ElementTree.Element("{%s}details" % ns_uri)

            root.append(instance.root)

        uri = self.get_uri(klass._URI, 'batch/update')
        data = self.tostring(ElementTree.ElementTree(root))
        self.post(uri, data)

    def create_batch(self, klass, list_kwargs):
        """
        Create using the batch create endpoint. It is only available for Sample and Container entities.

        :param klass: The class to use when creating the entity
                     (:py:class:`Sample <pyclarity_lims.entities.Sample>` or
                     :py:class:`Container <pyclarity_lims.entities.Container>`)
        :param list_kwargs: A list of dictionary where each dictionary will be used to create a instance of the klass.
                           Elements of the dictionary should match the keyword argument in the create method of
                           :py:class:`Sample <pyclarity_lims.entities.Sample>` or
                           :py:class:`Container <pyclarity_lims.entities.Container>`
        :returns: A list of the created entities in the same order as the list of kwargs.
        """
        if klass not in (Sample, Container):
            raise ValueError("Create batch is only supported for Containers and Samples not %s" % klass)
        instances = []
        # XML root element for batch request
        root = None
        for instance_kwargs in list_kwargs:
            instance = klass.create(self, nopost=True, **instance_kwargs)
            if root is None:
                # Tag is smp:details, con:details, etc.
                example_root = instance.root
                ns_uri = re.match("{(.*)}.*", example_root.tag).group(1)
                root = ElementTree.Element("{%s}details" % ns_uri)
            root.append(instance.root)
            instances.append(instance)
        uri = self.get_uri(klass._URI, 'batch/create')
        data = self.tostring(ElementTree.ElementTree(root))
        root = self.post(uri, data)
        for i, node in enumerate(root.getchildren()):
            # Rely on the order of the returned elements to set the uri link which is conserved
            instances[i]._uri = node.attrib['uri']
        return instances

    def route_artifacts(self, artifact_list, workflow_uri=None, stage_uri=None, unassign=False):
        """
        Take a list of artifacts and queue them to the stage specified by the stage uri. If a workflow uri is specified,
        the artifacts will be queued to the first stage of the workflow.

        :param artifact_list: list of Artifacts.
        :param workflow_uri: The uri of the workflow.
        :param stage_uri: The uri of the stage.
        :param unassign: If True, then the artifact will be removed from the queue instead of added.
        """
        root = ElementTree.Element(nsmap('rt:routing'))
        if unassign:
            s = ElementTree.SubElement(root, 'unassign')
        else:
            s = ElementTree.SubElement(root, 'assign')
        if workflow_uri:
            s.set('workflow-uri', workflow_uri)
        if stage_uri:
            s.set('stage-uri', stage_uri)
        for artifact in artifact_list:
            a = ElementTree.SubElement(s, 'artifact')
            a.set('uri', artifact.uri)

        uri = self.get_uri('route', 'artifacts')
        r = requests.post(uri, data=self.tostring(ElementTree.ElementTree(root)),
                          auth=(self.username, self.password),
                          headers={'content-type': 'application/xml',
                                   'accept': 'application/xml'})
        self.validate_response(r)

    def tostring(self, etree):
        """Return the ElementTree contents as a UTF-8 encoded XML string."""
        outfile = BytesIO()
        self.write(outfile, etree)
        return outfile.getvalue()

    def write(self, outfile, etree):
        """Write the ElementTree contents as UTF-8 encoded XML to the open file."""
        etree.write(outfile, encoding='utf-8', xml_declaration=True)
