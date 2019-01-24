from pyclarity_lims.constants import nsmap
from pyclarity_lims.descriptors import StringDescriptor, UdfDictionaryDescriptor, \
    UdtDictionaryDescriptor, ExternalidListDescriptor, EntityDescriptor, BooleanDescriptor, \
    DimensionDescriptor, IntegerDescriptor, \
    InputOutputMapList, LocationDescriptor, IntegerAttributeDescriptor, \
    StringAttributeDescriptor, EntityListDescriptor, StringListDescriptor, PlacementDictionaryDescriptor, \
    ReagentLabelList, AttributeListDescriptor, StringDictionaryDescriptor, OutputPlacementListDescriptor, \
    XmlActionList, MutableDescriptor, XmlPooledInputDict, QueuedArtifactList

try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urlparse import urlsplit, urlparse, parse_qs, urlunparse

from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)


class Entity(object):
    """
    Base abstract class for every entity in the LIMS database.
    An Entity corresponds to an XML document and as such it should have at least a uri or an id.
    """

    _TAG = None
    _URI = None
    _PREFIX = None
    _CREATION_PREFIX = None
    _CREATION_TAG = None

    def __new__(cls, lims, uri=None, id=None, _create_new=False):
        if not uri:
            if id:
                if cls._URI:
                    uri = lims.get_uri(cls._URI, id)
                else:
                    raise ValueError("%s requires a uri not an id" % cls.__name__)
            elif _create_new:
                # create the Object without id or uri
                pass
            else:
                raise ValueError("Entity uri and id can't be both None")
        try:
            return lims.cache[uri]
        except KeyError:
            return object.__new__(cls)

    def __init__(self, lims, uri=None, id=None, _create_new=False):
        assert uri or id or _create_new
        if not _create_new:
            if hasattr(self, 'lims'):
                return
            if not uri:
                uri = lims.get_uri(self._URI, id)
            lims.cache[uri] = self
            self.root = None
        self.lims = lims
        self._uri = uri
        self.root = None

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.id)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.uri)

    @property
    def uri(self):
        try:
            return self._uri
        except:
            return self._URI

    @property
    def id(self):
        """Return the LIMS id; obtained from the URI."""
        parts = urlsplit(self.uri)
        return parts.path.split('/')[-1]

    def get(self, force=False):
        """Get the XML data for this instance."""
        if not force and self.root is not None: return
        self.root = self.lims.get(self.uri)

    def put(self):
        """Save this instance by doing PUT of its serialized XML."""
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        return self.lims.put(self.uri, data)

    def post(self):
        """Save this instance with POST"""
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        return self.lims.post(self.uri, data)

    @classmethod
    def _create(cls, lims, **kwargs):
        """Create an instance from attributes and return it"""
        instance = cls(lims, _create_new=True)
        prefix = cls._CREATION_PREFIX
        if prefix is None:
            prefix = cls._PREFIX
        tag = cls._CREATION_TAG
        if tag is None:
            tag = cls._TAG
        if tag is None:
            tag = cls.__name__.lower()
        instance.root = ElementTree.Element(nsmap(prefix + ':' + tag))
        for attribute in kwargs:
            if hasattr(instance, attribute):
                setattr(instance, attribute, kwargs.get(attribute))
            else:
                raise TypeError("%s create: got an unexpected keyword argument '%s'" % (cls.__name__, attribute))

        return instance

    @classmethod
    def create(cls, lims, **kwargs):
        """Create an instance from attributes then post it to the LIMS"""
        post = not kwargs.pop('nopost', False)
        instance = cls._create(lims, **kwargs)
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        if post:
            instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
            instance._uri = instance.root.attrib['uri']
        return instance


class Lab(Entity):
    """A lab is a list of researchers."""

    _URI = 'labs'
    _PREFIX = 'lab'

    name = StringDescriptor('name')
    """Name of the lab"""
    billing_address = StringDictionaryDescriptor(tag='billing-address')
    """Billing address of the lab"""
    shipping_address = StringDictionaryDescriptor(tag='shipping-address')
    """Shipping address of the lab"""
    udf = UdfDictionaryDescriptor()
    """Dictionary of UDFs associated with the Lab"""
    udt = UdtDictionaryDescriptor()
    """Dictionary of UDTs associated with the Lab"""
    externalids = ExternalidListDescriptor()
    """List of external identifiers associated with the lab"""
    website = StringDescriptor('website')
    """URL to the lab website"""


class Researcher(Entity):
    """Person; client scientist or lab personnel. Associated with a lab."""

    _URI = 'researchers'
    _PREFIX = 'res'

    first_name = StringDescriptor('first-name')
    """First name of the researcher"""
    last_name = StringDescriptor('last-name')
    """Last name of the researcher"""
    phone = StringDescriptor('phone')
    """Phone number of the researcher"""
    fax = StringDescriptor('fax')
    """Fax number of the researcher"""
    email = StringDescriptor('email')
    """Email of the researcher"""
    initials = StringDescriptor('initials')
    """Initials of the researcher"""
    lab = EntityDescriptor('lab', Lab)
    """Lab associated with the researcher"""
    udf = UdfDictionaryDescriptor()
    """Dictionary of UDFs associated with the researcher"""
    udt = UdtDictionaryDescriptor()
    """Dictionary of UDTs associated with the researcher"""
    externalids = ExternalidListDescriptor()
    """List of external identifiers associated with the researcher"""

    # credentials XXX

    @property
    def name(self):
        """Complete name of the researcher"""
        return "%s %s" % (self.first_name, self.last_name)


class Reagent_label(Entity):
    """Reagent label element"""

    reagent_label = StringDescriptor('reagent-label')
    """The reagent label"""


class Note(Entity):
    """Note attached to a project or a sample."""

    content = StringDescriptor(None)  # root element
    """The content of the note"""


class File(Entity):
    """File attached to a project or a sample."""

    _URI = 'files'
    _PREFIX = 'file'

    attached_to = StringDescriptor('attached-to')
    """The uri of the Entity this file is attached to"""
    content_location = StringDescriptor('content-location')
    """The location of the file on the server"""
    original_location = StringDescriptor('original-location')
    """The original location of the file when it was uploaded"""
    is_published = BooleanDescriptor('is-published')
    """Whether the file is published or not"""


class Project(Entity):
    """Project concerning a number of samples; associated with a researcher."""

    _URI = 'projects'
    _PREFIX = 'prj'

    name = StringDescriptor('name')
    """The name of the project."""
    open_date = StringDescriptor('open-date')
    """The date at which the project was opened in format Year-Month-Day i.e. 2016-12-05. """
    close_date = StringDescriptor('close-date')
    """The date at which the project was closed in format Year-Month-Day i.e. 2016-12-05. """
    invoice_date = StringDescriptor('invoice-date')
    """The date at which the project was invoiced in format Year-Month-Day i.e. 2016-12-05. """
    researcher = EntityDescriptor('researcher', Researcher)
    """The researcher associated with the project."""
    udf = UdfDictionaryDescriptor()
    """Dictionary of UDFs associated with the project"""
    udt = UdtDictionaryDescriptor()
    """Dictionary of UDTs associated with the project"""
    files = EntityListDescriptor(tag=nsmap('file:file'), klass=File)
    """List of files attached to the project"""
    externalids = ExternalidListDescriptor()
    """List of external identifiers associated with the project"""
    # permissions XXX


class Sample(Entity):
    """Customer's sample to be analyzed; associated with a project."""

    _URI = 'samples'
    _PREFIX = 'smp'
    _CREATION_TAG = 'samplecreation'

    name = StringDescriptor('name')
    """Name of the sample."""
    date_received = StringDescriptor('date-received')
    """The date at which the sample was received in format Year-Month-Day i.e. 2016-12-05."""
    date_completed = StringDescriptor('date-completed')
    """The date at which the sample was completed in format Year-Month-Day i.e. 2016-12-05."""
    project = EntityDescriptor('project', Project)
    """The project associated with that sample."""
    submitter = EntityDescriptor('submitter', Researcher)
    """The researcher who submitted this sample."""
    # artifact: defined below
    udf = UdfDictionaryDescriptor()
    """Dictionary of UDFs associated with the sample."""
    udt = UdtDictionaryDescriptor()
    """Dictionary of UDTs associated with the sample."""
    notes = EntityListDescriptor(tag='note', klass=Note)
    """List of notes associated with the sample."""
    files = EntityListDescriptor(tag=nsmap('file:file'), klass=File)
    """List of files associated with the sample."""
    externalids = ExternalidListDescriptor()
    """List of external identifiers associated with the sample"""
    artifact = None  # See bottom of the file
    """Initial :py:class:`Artifact <pyclarity_lims.entities.Artifact>` associated with the sample."""

    @classmethod
    def create(cls, lims, container, position, **kwargs):
        """Create an instance of Sample from attributes then post it to the LIMS"""
        post = not kwargs.pop('nopost', False)
        if not isinstance(container, Container):
            raise TypeError('%s is not of type Container' % container)
        instance = super(Sample, cls)._create(lims, **kwargs)

        location = ElementTree.SubElement(instance.root, 'location')
        ElementTree.SubElement(location, 'container', dict(uri=container.uri))
        position_element = ElementTree.SubElement(location, 'value')
        position_element.text = position
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        if post:
            instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
            instance._uri = instance.root.attrib['uri']
        return instance


class Containertype(Entity):
    """Type of container for analyte artifacts."""

    _TAG = 'container-type'
    _URI = 'containertypes'
    _PREFIX = 'ctp'

    name = StringAttributeDescriptor('name')
    """Name of the type of container (Tube, 96 well plates, ...)"""
    calibrant_wells = StringListDescriptor(tag='calibrant-well')
    """If there are any wells on this container that are use for calibration. They would be defined here."""
    unavailable_wells = StringListDescriptor(tag='unavailable-well')
    """If there are any well on this container that should not be used. They would be defined here."""
    x_dimension = DimensionDescriptor('x-dimension')
    """Number of position on the x axis"""
    y_dimension = DimensionDescriptor('y-dimension')
    """Number of position on the y axis"""


class Container(Entity):
    """Container for analyte artifacts."""

    _URI = 'containers'
    _PREFIX = 'con'

    name = StringDescriptor('name')
    """Name of the container"""
    type = EntityDescriptor('type', Containertype)
    """:py:class:`Type <pyclarity_lims.entities.Containertype>` of the container."""
    occupied_wells = IntegerDescriptor('occupied-wells')
    """Number of wells occupied in the container."""
    placements = PlacementDictionaryDescriptor()
    """Dictionary of placements in a Container. The key is the location such as "A:1" and the value is the artifact in that well/tube."""
    udf = UdfDictionaryDescriptor()
    """Dictionary of UDFs associated with the container."""
    udt = UdtDictionaryDescriptor()
    """Dictionary of UDTs associated with the container."""
    state = StringDescriptor('state')
    """State of the container. e.g. Populated"""

    def get_placements(self):
        """Get the dictionary of locations and artifacts
        using the more efficient batch call."""
        result = self.placements.copy()
        self.lims.get_batch(list(result.values()))
        return result


class Processtype(Entity):
    _TAG = 'process-type'
    _URI = 'processtypes'
    _PREFIX = 'ptp'

    name = StringAttributeDescriptor('name')
    """Name of the process type."""
    # XXX


class Udfconfig(Entity):
    """Instance of field type (cnf namespace)."""
    _URI = 'configuration/udfs'

    name = StringDescriptor('name')
    """Name of the UDF."""
    attach_to_name = StringDescriptor('attach-to-name')
    """Name of entity type the UDF is attached to."""
    attach_to_category = StringDescriptor('attach-to-category')
    """_"""
    show_in_lablink = BooleanDescriptor('show-in-lablink')
    """Whether this UDF will be shown in lablink."""
    allow_non_preset_values = BooleanDescriptor('allow-non-preset-values')
    """Whether the UDF allows presets."""
    first_preset_is_default_value = BooleanDescriptor('first-preset-is-default-value')
    """Whether the first preset of the UDF is the default value."""
    show_in_tables = BooleanDescriptor('show-in-tables')
    """Whether the UDF can be shown in a table."""
    is_editable = BooleanDescriptor('is-editable')
    """Whether the UDF is editable."""
    is_deviation = BooleanDescriptor('is-deviation')
    """Whether the UDF is a deviation."""
    is_controlled_vocabulary = BooleanDescriptor('is-controlled-vocabulary')
    """Whether the UDF has a controled vocabulary."""
    presets = StringListDescriptor('preset')
    """List of presets."""


class Process(Entity):
    """Process (instance of Processtype) executed producing ouputs from inputs."""

    _URI = 'processes'
    _PREFIX = 'prc'
    _CREATION_PREFIX = 'prx'

    type = EntityDescriptor('type', Processtype)
    """The :py:class:`type <pyclarity_lims.entities.Processtype>` of the process"""
    date_run = StringDescriptor('date-run')
    """The date at which the process was finished in format Year-Month-Day i.e. 2016-12-05."""
    technician = EntityDescriptor('technician', Researcher)
    """The :py:class:`researcher <pyclarity_lims.entities.Researcher>` that started the step."""
    protocol_name = StringDescriptor('protocol-name')
    """The name of the protocol"""
    input_output_maps = InputOutputMapList()
    """
    List of tuples (input, output) where input and output item are dictionaries representing the input/output.
    Keys of the dict can be:

    * for the input:

        * post-process-uri: input :py:class:`Artifact <pyclarity_lims.entities.Artifact>`
        * uri: input :py:class:`Artifact <pyclarity_lims.entities.Artifact>`
        * limsid: lims id of the input artifact
        * parent-process: :py:class:`Process <pyclarity_lims.entities.Process>` that generated this input

    * for the output:

        * uri: output :py:class:`Artifact <pyclarity_lims.entities.Artifact>`
        * limsid: id of the Artifact generated
        * output-generation-type: type of output generation (example: PerInput)
        * output-type: type of artifact generated (Analyte, or ResultFile)

    """
    udf = UdfDictionaryDescriptor()
    """Dictionary of UDFs associated with the process. 
    
    Note that the UDFs cannot be modify in Process. Use :py:class:`Step details <pyclarity_lims.entities.StepDetails>`
    to modify UDFs instead. You can access them with process.step.details.udf"""
    udt = UdtDictionaryDescriptor()
    """Dictionary of UDTs associated with the process."""
    files = EntityListDescriptor(nsmap('file:file'), File)
    """List of :py:class:`files <pyclarity_lims.entities.File>` associated with the sample."""
    process_parameter = StringDescriptor('process-parameter')
    """Parameter for the process"""
    # instrument XXX
    # process_parameters XXX

    def outputs_per_input(self, inart, ResultFile=False, SharedResultFile=False, Analyte=False):
        """Getting all the output artifacts related to a particular input artifact

        :param inart: input artifact id or artifact entity use to select the output
        :param ResultFile: boolean specifying to only return ResultFiles.
        :param SharedResultFile: boolean specifying to only return SharedResultFiles.
        :param Analyte: boolean specifying to only return Analytes.
        :return: output artifact corresponding to the input artifact provided
        """
        if isinstance(inart, Artifact):
            inouts = [io for io in self.input_output_maps if io[0]['uri'] == inart]
        else:
            inouts = [io for io in self.input_output_maps if io[0]['limsid'] == inart]

        if ResultFile:
            inouts = [io for io in inouts if io[1]['output-type'] == 'ResultFile']
        elif SharedResultFile:
            inouts = [io for io in inouts if io[1]['output-type'] == 'SharedResultFile']
        elif Analyte:
            inouts = [io for io in inouts if io[1]['output-type'] == 'Analyte']
        outs = [io[1]['uri'] for io in inouts]
        return outs

    def input_per_sample(self, sample):
        """Getting all the input artifacts derived from the specified sample

        :param sample: the sample name to check against
        :return: list of input artifacts matching the sample name

        """
        ins_all = self.all_inputs()
        ins = []
        for inp in ins_all:
            for samp in inp.samples:
                if samp.name == sample and inp not in ins:
                    ins.append(inp)
        return ins

    def all_inputs(self, unique=True, resolve=False):
        """Retrieving all input artifacts from input_output_maps.
        If unique is true, no duplicates are returned.

        :param unique: boolean specifying if the list of artifacts should be uniqued
        :param resolve: boolean specifying if the artifacts entities should be resolved through a batch query.
        :return: list of input artifacts.
        """
        # if the process has no input, that is not standard and we want to know about it
        try:
            ids = [io[0]['limsid'] for io in self.input_output_maps]
        except TypeError:
            logger.error('Process ', self, ' has no input artifacts')
            raise TypeError
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch([Artifact(self.lims, id=id) for id in ids if id is not None])
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def all_outputs(self, unique=True, resolve=False):
        """Retrieving all output artifacts from input_output_maps.
        If unique is true, no duplicates are returned.

        :param unique: boolean specifying if the list of artifacts should be uniqued
        :param resolve: boolean specifying if the artifact entities should be resolved through a batch query.
        :return: list of output artifacts.

        """
        # Given how ids is structured, io[1] might be None: some process don't have an output.
        ids = [io[1]['limsid'] for io in self.input_output_maps if io[1] is not None]
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch([Artifact(self.lims, id=id) for id in ids if id is not None])
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def _output_files(self, resfile, output_generation_type):
        if output_generation_type:
            artifacts = [
                io[1]['uri'] for io in self.input_output_maps
                if io[1] is not None
                and io[1]['output-type'] == resfile
                and io[1]['output-generation-type'] == output_generation_type
            ]
        else:
            artifacts = [
                io[1]['uri'] for io in self.input_output_maps
                if io[1] is not None and io[1]['output-type'] == resfile
            ]
        return list(set(artifacts))

    def shared_result_files(self, output_generation_type=None):
        """Retrieve all output artifacts where output-type is SharedResultFile.

        :param output_generation_type: string specifying the output-generation-type (PerAllInputs or PerInput)
        :return: list of output artifacts.

        """
        return self._output_files('SharedResultFile', output_generation_type)

    def result_files(self, output_generation_type=None):
        """Retrieve all output artifacts where output-type is ResultFile.

        :param output_generation_type: string specifying the output-generation-type (PerAllInputs or PerInput)
        :return: list of output artifacts.

        """
        return self._output_files('ResultFile', output_generation_type)

    def analytes(self):
        """Retrieving the output Analytes of the process, if existing.
        If the process is not producing any output analytes, the input
        analytes are returned. Input/Output is returned as an information string.
        Makes aggregate processes and normal processes look the same."""
        info = 'Output'
        artifacts = self.all_outputs(unique=True)
        analytes = [a for a in artifacts if a.type == 'Analyte']
        if len(analytes) == 0:
            artifacts = self.all_inputs(unique=True)
            analytes = [a for a in artifacts if a.type == 'Analyte']
            info = 'Input'
        return analytes, info

    def parent_processes(self):
        """Retrieving all parent processes through the input artifacts"""
        return [i_a.parent_process for i_a in self.all_inputs(unique=True)]

    def output_containers(self):
        """Retrieve all unique output containers"""
        cs = []
        for o_a in self.all_outputs(unique=True):
            if o_a.container:
                cs.append(o_a.container)
        return list(frozenset(cs))

    @property
    def step(self):
        """Retrieve the Step corresponding to this process. They share the same id"""
        return Step(self.lims, id=self.id)


class Artifact(Entity):
    """Any process input or output; analyte or file."""

    _URI = 'artifacts'
    _PREFIX = 'art'

    name = StringDescriptor('name')
    """The name of the artifact."""
    type = StringDescriptor('type')
    """The type of the artifact: Analyte, ResultFile or SharedResultFile."""
    output_type = StringDescriptor('output-type')
    """The output-type of the Artifact"""
    parent_process = EntityDescriptor('parent-process', Process)
    """The :py:class:`parent process <pyclarity_lims.entities.Process>` that generated this artfact."""
    volume = StringDescriptor('volume')
    """_"""
    concentration = StringDescriptor('concentration')
    """_"""
    qc_flag = StringDescriptor('qc-flag')
    """The qc-flag applied to the Artifact. """
    location = LocationDescriptor('location')
    """The Artifact's location in a container."""
    working_flag = BooleanDescriptor('working-flag')
    """The working-flag of the Artifact."""
    samples = EntityListDescriptor('sample', Sample)
    """List of :py:class:`Samples <pyclarity_lims.entities.Sample>` associated with this artifact."""
    udf = UdfDictionaryDescriptor()
    """Dictionary of UDFs associated with the artifact."""
    files = EntityListDescriptor(nsmap('file:file'), File)
    """List of :py:class:`files <pyclarity_lims.entities.File>` associated with the artifact."""
    reagent_labels = ReagentLabelList()
    """List of :py:class:`Reagent labels <pyclarity_lims.entities.Reagent_label>` associated with the artifact."""
    workflow_stages = None  # See bottom of the file
    """List of workflow stage :py:class:`Steps <pyclarity_lims.entities.Step>` that this artifact ran through."""

    # artifact_flags XXX
    # artifact_groups XXX

    def input_artifact_list(self):
        """Returns the input artifact ids of the parent process."""
        input_artifact_list = []
        try:
            for iomap in self.parent_process.input_output_maps:
                if iomap[1]['limsid'] == self.id:
                    input_artifact_list.append(iomap[0]['uri'])  # ['limsid'])
        except:
            pass
        return input_artifact_list

    def get_state(self):
        """Parse out the state value from the URI."""
        parts = urlparse(self.uri)
        params = parse_qs(parts.query)
        try:
            return params['state'][0]
        except (KeyError, IndexError):
            return None

    @property
    def container(self):
        """The container where the artifact is located, or None"""
        try:
            return self.location[0]
        except:
            return None

    def stateless(self):
        """Return the artifact independently of its state"""
        parts = urlparse(self.uri)
        if 'state' in parts[4]:
            stateless_uri = urlunparse([parts[0], parts[1], parts[2], parts[3], '', ''])
            return Artifact(self.lims, uri=stateless_uri)
        else:
            return self

    # XXX set_state ?
    state = property(get_state)
    stateless = property(stateless)

    def _get_workflow_stages_and_statuses(self):
        self.get()
        result = []
        rootnode = self.root.find('workflow-stages')
        for node in rootnode.findall('workflow-stage'):
            result.append((Stage(self.lims, uri=node.attrib['uri']), node.attrib['status'], node.attrib['name']))
        return result

    workflow_stages_and_statuses = property(_get_workflow_stages_and_statuses)
    """List of tuples containing three elements (A, B, C) where:

        - A is a :py:class:`Step <pyclarity_lims.entities.Step>` this artifact has run through.
        - B is the status of said Step.
        - C the name of the Step.
    """


class ReagentKit(Entity):
    """Type of Reagent with information about the provider"""
    _URI = "reagentkits"
    _TAG = "reagent-kit"
    _PREFIX = 'kit'

    name = StringDescriptor('name')
    """Name of the reagent kit"""
    supplier = StringDescriptor('supplier')
    """Supplier for the reagent kit"""
    website = StringDescriptor('website')
    """Website associated with the reagent kit"""
    archived = BooleanDescriptor('archived')
    """Whether the reagent kit is archived or not"""


class ReagentLot(Entity):
    """Information about a particular regaent lot used in a step"""
    _URI = "reagentlots"
    _TAG = "reagent-lot"
    _PREFIX = "lot"

    reagent_kit = EntityDescriptor('reagent-kit', ReagentKit)
    """:py:class:`Reagent kit <pyclarity_lims.entities.ReagentKit>` associated with this lot."""
    name = StringDescriptor('name')
    """Name of the reagent lot"""
    lot_number = StringDescriptor('lot-number')
    """Lot number"""
    created_date = StringDescriptor('created-date')
    """The date at which the lot was created in format Year-Month-Day i.e. 2016-12-05."""
    last_modified_date = StringDescriptor('last-modified-date')
    """The date at which the lot was last modified in format Year-Month-Day i.e. 2016-12-05."""
    expiry_date = StringDescriptor('expiry-date')
    """The date at which the lot expires in format Year-Month-Day i.e. 2016-12-05."""
    created_by = EntityDescriptor('created-by', Researcher)
    """:py:class:`Researcher <pyclarity_lims.entities.Researcher>` that created that lot."""
    last_modified_by = EntityDescriptor('last-modified-by', Researcher)
    """:py:class:`Researcher <pyclarity_lims.entities.Researcher>` that last modified this lot."""
    status = StringDescriptor('status')
    """Status of the lot."""
    usage_count = IntegerDescriptor('usage-count')
    """Number of times the lot was used."""


class StepPlacements(Entity):
    """Placements from within a step. Supports POST"""

    selected_containers = EntityListDescriptor(tag='container', klass=Container, nesting=['selected-containers'])
    """List of :py:class:`containers <pyclarity_lims.entities.Container>`"""
    _placement_list = OutputPlacementListDescriptor()

    def get_placement_list(self):
        return self._placement_list

    def set_placement_list(self, value):
        self._placement_list = value
        self.selected_containers = list(set([p[1][0] for p in self.placement_list]))

    placement_list = property(get_placement_list, set_placement_list)
    """
    List of tuples (A, (B, C)) where:

    - A is an :py:class:`artifact <pyclarity_lims.entities.Artifact>`
    - B is a :py:class:`container <pyclarity_lims.entities.Container>`
    - C is a string specifying the location in the container such as "1:1"
    """

    def get_selected_containers(self):
        return self.selected_containers


class StepActions(Entity):
    """Actions associated with the end of the step"""
    _escalation = None
    next_actions = MutableDescriptor(XmlActionList)
    """
    List of dicts that represent an action for an artifact. They keys of the dict are:
        - artifact: The :py:class:`artifact <pyclarity_lims.entities.Artifact>` associated with this Action
        - step: The next :py:class:`step <pyclarity_lims.entities.Step>` associated with this action
        - rework-step: The :py:class:`step <pyclarity_lims.entities.Step>` associated with this action when the Artifact needs to be requeued
        - action: The type of action to perform.
            - leave: Leave the sample in the QC protocol.
            - repeat: Repeat this step.
            - remove: Remove from workflow.
            - review: Request manager review.
            - complete: Mark protocol as complete.
            - store: Store for later.
            - nextstep: Continue to the next step.
            - rework: Rework from an earlier step.
            - completerepeat: Complete and Repeat
            - unknown: The action is unknown.
        """
    step = None  # See bottom of the file
    """:py:class:`Step <pyclarity_lims.entities.Step>` associated with the actions."""

    @property
    def escalation(self):
        # TODO: Convert to use descriptors and document
        if not self._escalation:
            self.get()
            self._escalation = {}
            for node in self.root.findall('escalation'):
                self._escalation['artifacts'] = []
                self._escalation['author'] = Researcher(self.lims,
                                                        uri=node.find('request').find('author').attrib.get('uri'))
                self._escalation['request'] = node.find('request').find('comment').text
                if node.find('review') is not None:  # recommended by the Etree doc
                    self._escalation['status'] = 'Reviewed'
                    self._escalation['reviewer'] = Researcher(self.lims,
                                                              uri=node.find('review').find('author').attrib.get('uri'))
                    self._escalation['answer'] = node.find('review').find('comment').text
                else:
                    self._escalation['status'] = 'Pending'

                for node2 in node.findall('escalated-artifacts'):
                    art = self.lims.get_batch([Artifact(self.lims, uri=ch.attrib.get('uri')) for ch in node2])
                    self._escalation['artifacts'].extend(art)
        return self._escalation


class StepReagentLots(Entity):
    reagent_lots = EntityListDescriptor('reagent-lot', ReagentLot, nesting=['reagent-lots'])
    """List of :py:class:`ReagentLots <pyclarity_lims.entities.ReagentLot>`"""


class StepDetails(Entity):
    """Details associated with a step"""

    input_output_maps = InputOutputMapList(nesting=['input-output-maps'])
    """
        List of tuples (input, output) where input and output item are dictionaries representing the input/output.
        Keys of the dict can be:

        * for the input:
            * post-process-uri: input :py:class:`Artifact <pyclarity_lims.entities.Artifact>`
            * uri: input :py:class:`Artifact <pyclarity_lims.entities.Artifact>`
            * limsid: lims id of the input artifact
            * parent-process: :py:class:`Process <pyclarity_lims.entities.Process>` that generated this input

        * for the output:
            * uri: output :py:class:`Artifact <pyclarity_lims.entities.Artifact>`
            * limsid: id of the Artifact generated
            * output-generation-type: type of output generation (example: PerInput)
            * output-type: type of artifact generated (Analyte, or ResultFile)
    """
    udf = UdfDictionaryDescriptor(nesting=['fields'])
    """Dictionary of UDFs associated with the step"""
    udt = UdtDictionaryDescriptor(nesting=['fields'])
    """Dictionary of UDTs associated with the step"""


class StepProgramStatus(Entity):
    """Status displayed in the step"""

    status = StringDescriptor('status')
    """Status of the program"""
    message = StringDescriptor('message')
    """Message returned by the program"""


class StepPools(Entity):
    pooled_inputs = MutableDescriptor(XmlPooledInputDict)
    """Dictionary where the keys are the pool names and the values are tuples (pool, inputs) representing a pool.
    Each tuple has two elements:

        * an output Artifact containing the pool.
        * a tuple containing the input artifacts for that pool.
    """
    available_inputs = EntityListDescriptor(tag='input', klass=Artifact, nesting=['available-inputs'])
    """List of artifact available for pooling. 
    
    Note that adding artifacts to a pool will not remove them from this list until put() is run.
    """

    def put(self):
        self.root = super(StepPools, self).put()
        return self.root


class Step(Entity):
    """Step, as defined by the genologics API."""

    _URI = 'steps'
    _PREFIX = 'stp'
    _CREATION_TAG = 'step-creation'

    current_state = StringAttributeDescriptor('current-state')
    """The current state of the step."""
    _reagent_lots = EntityDescriptor('reagent-lots', StepReagentLots)
    actions = EntityDescriptor('actions', StepActions)
    """Link to the :py:class:`StepActions <pyclarity_lims.entities.StepActions>` entity"""
    placements = EntityDescriptor('placements', StepPlacements)
    """Link to the :py:class:`StepPlacements <pyclarity_lims.entities.StepPlacements>` entity"""
    details = EntityDescriptor('details', StepDetails)
    """Link to the :py:class:`StepDetails <pyclarity_lims.entities.StepDetails>` entity"""
    program_status = EntityDescriptor('program-status', StepProgramStatus)
    """Link to the :py:class:`StepProgramStatus <pyclarity_lims.entities.StepProgramStatus>` entity"""
    pools = EntityDescriptor('pools', StepPools)
    """Link to the :py:class:`StepPools <pyclarity_lims.entities.StepPools>` entity"""
    date_started = StringDescriptor('date-started')
    """The date at which the step started in format Year-Month-DayTHour:Min:Sec, e.g. 2016-11-22T10:43:32.857+00:00"""
    date_completed = StringDescriptor('date-completed')
    """The date at which the step completed in format Year-Month-DayTHour:Min:Sec, e.g. 2016-11-22T10:43:32.857+00:00"""
    _available_programs = None
    configuration = None
    """:py:class:`Step configuration<pyclarity_lims.entities.ProtocolStep>` associated with the step."""

    def advance(self):
        """
        Send a post query to advance the step to the next step
        """
        self.get()
        self.root = self.lims.post(
            uri="{}/advance".format(self.uri),
            data=self.lims.tostring(ElementTree.ElementTree(self.root))
        )

    @property
    def reagent_lots(self):
        """List of reagent lots"""
        if self._reagent_lots:
            return self._reagent_lots.reagent_lots

    @property
    def available_programs(self):
        """
        List of available programs to trigger.
        Each element is a tuple with the name and the trigger uri
        """
        self.get()
        if not self._available_programs:
            self._available_programs = []
            available_programs_et = self.root.find('available-programs')
            if available_programs_et is not None and len(available_programs_et) > 0:
                for ap in available_programs_et.findall('available-program'):
                    self._available_programs.append((ap.attrib['name'], ap.attrib['uri']))
        return self._available_programs

    @property
    def program_names(self):
        """List of available program names."""
        return [ap[0] for ap in self.available_programs]

    def trigger_program(self, name):
        """
        Trigger a program of the provided name.

        :param name: the name of the program.
        :return: the program status.
        :raise ValueError: if the program does not exist.
        """
        progs = [ap[1] for ap in self.available_programs if name == ap[0]]
        if not progs:
            raise ValueError('%s not in available program names' % name)
        e = self.lims.post(progs[0], data=None)
        self.program_status = StepProgramStatus(self.lims, uri=e.attrib['uri'])
        self.program_status.root = e
        return self.program_status

    @property
    def process(self):
        """Retrieve the Process corresponding to this Step. They share the same id"""
        return Process(self.lims, id=self.id)

    def set_placements(self, output_containers, output_placement_list):
        """
        Create a new placement for a new step.
        This method also modifies the selected containers with the provided output container.
        It is meant to be used with a newly created step that does not have a placement yet.

        :param output_containers: List of :py:class:`Containers <pyclarity_lims.entities.Container>`
                                  used to store the output artifacts.
        :param output_placement_list: List of tuples (A, (B, C)) where:

            - A is an :py:class:`artifact <pyclarity_lims.entities.Artifact>`,
            - B is a :py:class:`container <pyclarity_lims.entities.Container>`,
            - C is a string specifying the location in the container such as "1:1"

        """
        self.placements = StepPlacements(self.lims, uri=self.uri + '/placements')
        self.placements.selected_containers = output_containers
        self.placements.placement_list = output_placement_list
        self.placements.root = self.placements.post()

    @classmethod
    def create(cls, lims, protocol_step, inputs, container_type_name=None, reagent_category=None, replicates=1, **kwargs):
        """
        Create a new instance of a Step. This method will start a step from queued artifacts.

        :param lims: Lims connection object
        :param protocol_step: the :py:class:`ProtocolStep <pyclarity_lims.entities.ProtocolStep>` specifying the step to start.
        :param inputs: A list of :py:class:`artifacts <pyclarity_lims.entities.Artifact>` as input to the step.
                       These need to be queued for that step for the query to be successful.
        :param container_type_name: optional name of the type of container that this step use for its output.
                                    if omitted it uses the required type from the ProtocolStep if there is only one.
        :param reagent_category: optional reagent_category.
        :param replicates: int or list of ints specifying the number of replicates for each inputs.
        """
        instance = super(Step, cls)._create(lims, **kwargs)
        # Check configuratio of the step
        if not isinstance(protocol_step, ProtocolStep):
            raise TypeError('protocol_step must be of type ProtocolStep not %s.' % type(protocol_step))
        configuration_node = ElementTree.SubElement(instance.root, 'configuration')
        configuration_node.attrib['uri'] = protocol_step.uri
        configuration_node.text = protocol_step.name

        # Check container name
        # Default to the require type if not provided and only possible choice
        if not container_type_name and len(protocol_step.permitted_containers) == 1:
            container_type_name = protocol_step.permitted_containers[0]
        if protocol_step.permitted_containers and container_type_name in protocol_step.permitted_containers:
            container_type_node = ElementTree.SubElement(instance.root, 'container-type')
            container_type_node.text = container_type_name
        elif protocol_step.permitted_containers:
            # TODO: raise early if the container type name is required and missing or not in permitted type
            pass

        # TODO: more work needed to understand how the permitted reagent applies here
        if reagent_category:
            reagent_category_node = ElementTree.SubElement(instance.root, 'reagent_category')
            reagent_category_node.text = reagent_category

        if isinstance(replicates, int):
            replicates = [replicates] * len(inputs)
        assert len(replicates) == len(inputs)
        inputs_node = ElementTree.SubElement(instance.root, 'inputs')
        for i, artifact in enumerate(inputs):
            if not isinstance(artifact, Artifact):
                raise TypeError('Input must be of type Artifact not %s.' % type(artifact))
            input_node = ElementTree.SubElement(inputs_node, 'input')
            input_node.attrib['uri'] = artifact.uri
            if replicates:
                input_node.attrib['replicates'] = str(replicates[i])
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib['uri']
        return instance


class ProtocolStep(Entity):
    """Steps key in the Protocol object"""

    _TAG = 'step'

    name = StringAttributeDescriptor('name')
    """Name of the step"""
    type = EntityDescriptor('process-type', Processtype)
    """:py:class:`Processtype <pyclarity_lims.entities.Processtype>` associated with this step."""
    permitted_containers = StringListDescriptor('container-type', nesting=['permitted-containers'])
    """List of names for the permitted container type in that step."""
    queue_fields = AttributeListDescriptor('queue-field', nesting=['queue-fields'])
    """List of dicts describing the fields available in that step's queue."""
    step_fields = AttributeListDescriptor('step-field', nesting=['step-fields'])
    """List of dicts describing the fields available in that step's UDF."""
    sample_fields = AttributeListDescriptor('sample-field', nesting=['sample-fields'])
    """List of dicts describing the field available in that step's sample view."""
    step_properties = AttributeListDescriptor('step-property', nesting=['step-properties'])
    """List of dicts describing the properties of this step."""
    epp_triggers = AttributeListDescriptor('epp-trigger', nesting=['epp-triggers'])
    """List of dicts describing the EPP trigger attached to this step."""

    @property
    def queue(self):
        """The queue associated with this protocol step. The link is possible because they share the same id."""
        return Queue(self.lims, id=self.id)


class Protocol(Entity):
    """Protocol, holding ProtocolSteps and protocol-properties"""
    _URI = 'configuration/protocols'
    _TAG = 'protocol'

    steps = EntityListDescriptor('step', ProtocolStep, nesting=['steps'])
    """List of :py:class:`steps <pyclarity_lims.entities.ProtocolStep>`"""
    properties = AttributeListDescriptor('protocol-property', nesting=['protocol-properties'])
    """List of dicts describing the protocol's property."""


class Stage(Entity):
    """Holds Protocol/Workflow"""
    name = StringAttributeDescriptor('name')
    """Name of the stage."""
    index = IntegerAttributeDescriptor('index')
    """Position of the stage in the protocol."""
    protocol = EntityDescriptor('protocol', Protocol)
    """:py:class:`Protocol <pyclarity_lims.entities.Protocol>` associated with this stage."""
    step = EntityDescriptor('step', ProtocolStep)
    """:py:class:`Step <pyclarity_lims.entities.ProtocolStep>` associated with this stage."""
    workflow = None  # See bottom of the file
    """:py:class:`Workflow <pyclarity_lims.entities.Workflow>` associated with the stage."""


class Workflow(Entity):
    """Workflow, introduced in 3.5"""
    _URI = "configuration/workflows"
    _TAG = "workflow"

    name = StringAttributeDescriptor("name")
    """Name of the workflow."""
    status = StringAttributeDescriptor("status")
    """Status of the workflow."""
    protocols = EntityListDescriptor('protocol', Protocol, nesting=['protocols'])
    """List of :py:class:`protocols <pyclarity_lims.entities.Protocol>` associated with this workflow."""
    stages = EntityListDescriptor('stage', Stage, nesting=['stages'])
    """List of :py:class:`stages <pyclarity_lims.entities.Stage>` associated with this workflow."""


class ReagentType(Entity):
    """Reagent Type, usually indexes for sequencing"""
    _URI = "reagenttypes"
    _TAG = "reagent-type"
    _PREFIX = 'rtp'

    category = StringDescriptor('reagent-category')
    """Reagent category associated with the type"""

    def __init__(self, lims, uri=None, id=None):
        super(ReagentType, self).__init__(lims, uri, id)
        assert self.uri is not None
        self.root = lims.get(self.uri)
        self.sequence = None
        for t in self.root.findall('special-type'):
            if t.attrib.get('name') == 'Index':
                for child in t.findall('attribute'):
                    if child.attrib.get('name') == 'Sequence':
                        self.sequence = child.attrib.get('value')


class Queue(Entity):
    """Queue of a given workflow stage"""
    _URI = 'queues'
    _TAG = 'queue'
    _PREFIX = 'que'

    queued_artifacts = MutableDescriptor(QueuedArtifactList)
    """
    List of :py:class:`artifacts <pyclarity_lims.entities.Artifact>` associated with this workflow stage
    alongside the time they've been added to that queue and the container they're in.
    The list contains tuples organised in the form (A, B, (C, D)), where:

         - A is an :py:class:`artifact <pyclarity_lims.entities.Artifact>`
         - B is a :py:class:`datetime <datetime.datetime>` object,
         - C is a :py:class:`container <pyclarity_lims.entities.Container>`
         - D is a string specifying the location such as "1:1"
    """

    @property
    def artifacts(self):
        """List of :py:class:`artifacts <pyclarity_lims.entities.Artifact>` associated with this workflow stage."""
        return [i[0] for i in self.queued_artifacts]


Sample.artifact = EntityDescriptor('artifact', Artifact)
StepActions.step = EntityDescriptor('step', Step)
Stage.workflow = EntityDescriptor('workflow', Workflow)
Artifact.workflow_stages = EntityListDescriptor(tag='workflow-stage', klass=Stage, nesting=['workflow-stages'])
Step.configuration = EntityDescriptor('configuration', ProtocolStep)
