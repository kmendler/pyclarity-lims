"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""
from pyclarity_lims.constants import nsmap
from pyclarity_lims.descriptors import StringDescriptor, UdfDictionaryDescriptor, \
    UdtDictionaryDescriptor, ExternalidListDescriptor, EntityDescriptor, BooleanDescriptor, \
    DimensionDescriptor, IntegerDescriptor, \
    InputOutputMapList, LocationDescriptor, IntegerAttributeDescriptor, \
    StringAttributeDescriptor, EntityListDescriptor, StringListDescriptor, PlacementDictionaryDescriptor, \
    ReagentLabelList, AttributeListDescriptor, StringDictionaryDescriptor, OutputPlacementListDescriptor
try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urlparse import urlsplit, urlparse, parse_qs, urlunparse

from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)


class Entity(object):
    "Base class for the entities in the LIMS database."

    _TAG = None
    _URI = None
    _PREFIX = None
    _CREATION_PREFIX = None
    _CREATION_TAG = None

    def __new__(cls, lims, uri=None, id=None, _create_new=False):
        if not uri:
            if id:
                uri = lims.get_uri(cls._URI, id)
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
            if hasattr(self, 'lims'): return
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
        "Return the LIMS id; obtained from the URI."
        parts = urlsplit(self.uri)
        return parts.path.split('/')[-1]

    def get(self, force=False):
        "Get the XML data for this instance."
        if not force and self.root is not None: return
        self.root = self.lims.get(self.uri)

    def put(self):
        "Save this instance by doing PUT of its serialized XML."
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        self.lims.put(self.uri, data)

    def post(self):
        "Save this instance with POST"
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        self.lims.post(self.uri, data)

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
        instance = cls._create(lims, **kwargs)
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib['uri']
        return instance


class Lab(Entity):
    "Lab; container of researchers."

    _URI = 'labs'
    _PREFIX = 'lab'

    name             = StringDescriptor('name')
    billing_address  = StringDictionaryDescriptor(tag='billing-address')
    shipping_address = StringDictionaryDescriptor(tag='shipping-address')
    udf              = UdfDictionaryDescriptor()
    udt              = UdtDictionaryDescriptor()
    externalids      = ExternalidListDescriptor()
    website          = StringDescriptor('website')


class Researcher(Entity):
    "Person; client scientist or lab personnel. Associated with a lab."

    _URI = 'researchers'
    _PREFIX = 'res'

    first_name  = StringDescriptor('first-name')
    last_name   = StringDescriptor('last-name')
    phone       = StringDescriptor('phone')
    fax         = StringDescriptor('fax')
    email       = StringDescriptor('email')
    initials    = StringDescriptor('initials')
    lab         = EntityDescriptor('lab', Lab)
    udf         = UdfDictionaryDescriptor()
    udt         = UdtDictionaryDescriptor()
    externalids = ExternalidListDescriptor()

    # credentials XXX

    @property
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)


class Reagent_label(Entity):
    """Reagent label element"""
    reagent_label = StringDescriptor('reagent-label')


class Note(Entity):
    "Note attached to a project or a sample."

    content = StringDescriptor(None)  # root element


class File(Entity):
    "File attached to a project or a sample."

    attached_to       = StringDescriptor('attached-to')
    content_location  = StringDescriptor('content-location')
    original_location = StringDescriptor('original-location')
    is_published      = BooleanDescriptor('is-published')


class Project(Entity):
    "Project concerning a number of samples; associated with a researcher."

    _URI = 'projects'
    _PREFIX = 'prj'

    name         = StringDescriptor('name')
    open_date    = StringDescriptor('open-date')
    close_date   = StringDescriptor('close-date')
    invoice_date = StringDescriptor('invoice-date')
    researcher   = EntityDescriptor('researcher', Researcher)
    udf          = UdfDictionaryDescriptor()
    udt          = UdtDictionaryDescriptor()
    files        = EntityListDescriptor(tag=nsmap('file:file'), klass=File)
    externalids  = ExternalidListDescriptor()
    # permissions XXX


class Sample(Entity):
    "Customer's sample to be analyzed; associated with a project."

    _URI = 'samples'
    _PREFIX = 'smp'
    _CREATION_TAG = 'samplecreation'

    name           = StringDescriptor('name')
    date_received  = StringDescriptor('date-received')
    date_completed = StringDescriptor('date-completed')
    project        = EntityDescriptor('project', Project)
    submitter      = EntityDescriptor('submitter', Researcher)
    # artifact: defined below
    udf            = UdfDictionaryDescriptor()
    udt            = UdtDictionaryDescriptor()
    notes          = EntityListDescriptor(tag='note', klass=Note)
    files          = EntityListDescriptor(tag=nsmap('file:file'), klass=File)
    externalids    = ExternalidListDescriptor()
    # biosource XXX


    @classmethod
    def create(cls, lims, container, position, **kwargs):
        """Create an instance of Sample from attributes then post it to the LIMS"""
        if not isinstance(container, Container):
            raise TypeError('%s is not of type Container'%container)
        instance = super(Sample, cls)._create(lims, **kwargs)

        location = ElementTree.SubElement(instance.root, 'location')
        ElementTree.SubElement(location, 'container', dict(uri=container.uri))
        position_element = ElementTree.SubElement(location, 'value')
        position_element.text = position
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib['uri']
        return instance


class Containertype(Entity):
    "Type of container for analyte artifacts."

    _TAG = 'container-type'
    _URI = 'containertypes'
    _PREFIX = 'ctp'

    name              = StringAttributeDescriptor('name')
    calibrant_wells   = StringListDescriptor(tag='calibrant-well')
    unavailable_wells = StringListDescriptor(tag='unavailable-well')
    x_dimension       = DimensionDescriptor('x-dimension')
    y_dimension       = DimensionDescriptor('y-dimension')


class Container(Entity):
    "Container for analyte artifacts."

    _URI = 'containers'
    _PREFIX = 'con'

    name           = StringDescriptor('name')
    type           = EntityDescriptor('type', Containertype)
    occupied_wells = IntegerDescriptor('occupied-wells')
    placements     = PlacementDictionaryDescriptor()
    udf            = UdfDictionaryDescriptor()
    udt            = UdtDictionaryDescriptor()
    state          = StringDescriptor('state')

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
    # XXX


class Udfconfig(Entity):
    "Instance of field type (cnf namespace)."
    _URI = 'configuration/udfs'

    name                          = StringDescriptor('name')
    attach_to_name                = StringDescriptor('attach-to-name')
    attach_to_category            = StringDescriptor('attach-to-category')
    show_in_lablink               = BooleanDescriptor('show-in-lablink')
    allow_non_preset_values       = BooleanDescriptor('allow-non-preset-values')
    first_preset_is_default_value = BooleanDescriptor('first-preset-is-default-value')
    show_in_tables                = BooleanDescriptor('show-in-tables')
    is_editable                   = BooleanDescriptor('is-editable')
    is_deviation                  = BooleanDescriptor('is-deviation')
    is_controlled_vocabulary      = BooleanDescriptor('is-controlled-vocabulary')
    presets                       = StringListDescriptor('preset')



class Process(Entity):
    "Process (instance of Processtype) executed producing ouputs from inputs."

    _URI = 'processes'
    _PREFIX = 'prc'
    _CREATION_PREFIX = 'prx'

    type              = EntityDescriptor('type', Processtype)
    date_run          = StringDescriptor('date-run')
    technician        = EntityDescriptor('technician', Researcher)
    protocol_name     = StringDescriptor('protocol-name')
    input_output_maps = InputOutputMapList()
    udf               = UdfDictionaryDescriptor()
    udt               = UdtDictionaryDescriptor()
    files             = EntityListDescriptor(nsmap('file:file'), File)
    process_parameter = StringDescriptor('process-parameter')

    # instrument XXX
    # process_parameters XXX

    def outputs_per_input(self, inart, ResultFile=False, SharedResultFile=False, Analyte=False):
        """Getting all the output artifacts related to a particual input artifact"""

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
        """gettiung all the input artifacts dereved from the specifyed sample"""
        ins_all = self.all_inputs()
        ins = []
        for inp in ins_all:
            for samp in inp.samples:
                if samp.name == sample and inp not in ins:
                    ins.append(inp)
        return ins

    def all_inputs(self, unique=True, resolve=False):
        """Retrieving all input artifacts from input_output_maps
        if unique is true, no duplicates are returned.
        """
        # if the process has no input, that is not standard and we want to know about it
        try:
            ids = [io[0]['limsid'] for io in self.input_output_maps]
        except TypeError:
            logger.error("Process ", self, " has no input artifacts")
            raise TypeError
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch([Artifact(self.lims, id=id) for id in ids if id is not None])
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def all_outputs(self, unique=True, resolve=False):
        """Retrieving all output artifacts from input_output_maps
        if unique is true, no duplicates are returned.
        """
        # Given how ids is structured, io[1] might be None : some process don't have an output.
        ids = [io[1]['limsid'] for io in self.input_output_maps if io[1] is not None]
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch([Artifact(self.lims, id=id) for id in ids if id is not None])
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def shared_result_files(self):
        """Retreve all resultfiles of output-generation-type PerAllInputs."""
        artifacts = self.all_outputs(unique=True)
        return [a for a in artifacts if a.output_type == 'SharedResultFile']

    def result_files(self):
        """Retreve all resultfiles of output-generation-type perInput."""
        artifacts = self.all_outputs(unique=True)
        return [a for a in artifacts if a.output_type == 'ResultFile']

    def analytes(self):
        """Retreving the output Analytes of the process, if existing.
        If the process is not producing any output analytes, the input
        analytes are returned. Input/Output is returned as a information string.
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
    "Any process input or output; analyte or file."

    _URI = 'artifacts'
    _PREFIX = 'art'

    name           = StringDescriptor('name')
    type           = StringDescriptor('type')
    output_type    = StringDescriptor('output-type')
    parent_process = EntityDescriptor('parent-process', Process)
    volume         = StringDescriptor('volume')
    concentration  = StringDescriptor('concentration')
    qc_flag        = StringDescriptor('qc-flag')
    location       = LocationDescriptor('location')
    working_flag   = BooleanDescriptor('working-flag')
    samples        = EntityListDescriptor('sample', Sample)
    udf            = UdfDictionaryDescriptor()
    files          = EntityListDescriptor(nsmap('file:file'), File)
    reagent_labels = ReagentLabelList()

    # artifact_flags XXX
    # artifact_groups XXX

    def input_artifact_list(self):
        """Returns the input artifact ids of the parrent process."""
        input_artifact_list = []
        try:
            for tuple in self.parent_process.input_output_maps:
                if tuple[1]['limsid'] == self.id:
                    input_artifact_list.append(tuple[0]['uri'])  # ['limsid'])
        except:
            pass
        return input_artifact_list

    def get_state(self):
        "Parse out the state value from the URI."
        parts = urlparse(self.uri)
        params = parse_qs(parts.query)
        try:
            return params['state'][0]
        except (KeyError, IndexError):
            return None

    @property
    def container(self):
        "The container where the artifact is located, or None"
        try:
            return self.location[0]
        except:
            return None

    def stateless(self):
        "returns the artefact independently of it's state"
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


class StepPlacements(Entity):
    """Placements from within a step. Supports POST"""
    _placementslist = None

    selected_containers = EntityListDescriptor(tag='container', klass=Container, nesting=['selected-containers'])
    _placement_list      = OutputPlacementListDescriptor()

    def get_placement_list(self):
        return self._placement_list

    def set_placement_list(self, value):
        self._placement_list = value
        self.selected_containers = list(set([p[1][0] for p in self.placement_list]))

    placement_list = property(get_placement_list, set_placement_list)

    def get_selected_containers(self):
        return self.selected_containers


class StepActions(Entity):
    """Actions associated with a step"""
    _escalation = None
    next_actions = AttributeListDescriptor(tag='next-action', nesting=['next-actions'])

    @property
    def escalation(self):
        if not self._escalation:
            self.get()
            self._escalation = {}
            for node in self.root.findall('escalation'):
                self._escalation['artifacts'] = []
                self._escalation['author'] = Researcher(self.lims,
                                                        uri=node.find('request').find('author').attrib.get('uri'))
                self._escalation['request'] = uri = node.find('request').find('comment').text
                if node.find('review') is not None:  # recommended by the Etree doc
                    self._escalation['status'] = 'Reviewed'
                    self._escalation['reviewer'] = Researcher(self.lims,
                                                              uri=node.find('review').find('author').attrib.get('uri'))
                    self._escalation['answer'] = uri = node.find('review').find('comment').text
                else:
                    self._escalation['status'] = 'Pending'

                for node2 in node.findall('escalated-artifacts'):
                    art = self.lims.get_batch([Artifact(self.lims, uri=ch.attrib.get('uri')) for ch in node2])
                    self._escalation['artifacts'].extend(art)
        return self._escalation


class ReagentKit(Entity):
    """Type of Reagent with information about the provider"""
    _URI = "reagentkits"
    _TAG = "reagent-kit"
    _PREFIX = 'kit'

    name     = StringDescriptor('name')
    supplier = StringDescriptor('supplier')
    website  = StringDescriptor('website')
    archived = BooleanDescriptor('archived')


class ReagentLot(Entity):
    """Reagent Lots contain information about a particualr lot of reagent used in a step"""
    _URI = "reagentlots"
    _TAG = "reagent-lot"
    _PREFIX = 'lot'

    reagent_kit        = EntityDescriptor('reagent-kit', ReagentKit)
    name               = StringDescriptor('name')
    lot_number         = StringDescriptor('lot-number')
    created_date       = StringDescriptor('created-date')
    last_modified_date = StringDescriptor('last-modified-date')
    expiry_date        = StringDescriptor('expiry-date')
    created_by         = EntityDescriptor('created-by', Researcher)
    last_modified_by   = EntityDescriptor('last-modified-by', Researcher)
    status             = StringDescriptor('status')
    usage_count        = IntegerDescriptor('usage-count')


class StepReagentLots(Entity):
    reagent_lots = EntityListDescriptor('reagent-lot', ReagentLot, nesting=['reagent-lots'])


class StepDetails(Entity):
    """Detail associated with a step"""

    input_output_maps = InputOutputMapList(nesting=['input-output-maps'])
    udf = UdfDictionaryDescriptor(nesting=['fields'])
    udt = UdtDictionaryDescriptor(nesting=['fields'])


class StepProgramStatus(Entity):
    """Status display in the step"""

    status  = StringDescriptor('status')
    message = StringDescriptor('message')


class Step(Entity):
    "Step, as defined by the genologics API."

    _URI = 'steps'
    _PREFIX = 'stp'
    _CREATION_TAG = 'step-creation'

    current_state  = StringAttributeDescriptor('current-state')
    _reagent_lots  = EntityDescriptor('reagent-lots', StepReagentLots)
    actions        = EntityDescriptor('actions', StepActions)
    placements     = EntityDescriptor('placements', StepPlacements)
    details        = EntityDescriptor('details', StepDetails)
    program_status = EntityDescriptor('program-status', StepProgramStatus)
    date_started   = StringDescriptor('date-started')
    date_completed = StringDescriptor('date-completed')
    _available_programs = None

    def advance(self):
        self.root = self.lims.post(
            uri="{}/advance".format(self.uri),
            data=self.lims.tostring(ElementTree.ElementTree(self.root))
        )

    @property
    def reagent_lots(self):
        if self._reagent_lots:
            return self._reagent_lots.reagent_lots

    @property
    def available_programs(self):
        self.get()
        if not self._available_programs:
            self._available_programs = []
            available_programs_et = self.root.find('available-programs')
            if available_programs_et:
                for ap in available_programs_et.findall('available-program'):
                    self._available_programs.append((ap.attrib['name'], ap.attrib['uri']))
        return self._available_programs

    @property
    def program_names(self):
        return [ap[0] for ap in self.available_programs]

    def trigger_program(self, name):
        progs = [ap[1] for ap in self.available_programs if name == ap[0]]
        if not progs:
            raise ValueError('%s not in available program names' % name)
        e = self.lims.post(progs[0], data=None)
        self.program_status = StepProgramStatus(self.lims, uri=e.attrib['uri'])
        self.program_status.root = e
        return self.program_status

    def process(self):
        """Retrieve the Process corresponding to this Step. They share the same id"""
        return Process(self.lims, id=self.id)

    def set_placements(self, output_containers, output_placement_list):
        self.placement = StepPlacements(self.lims, uri=self.uri + '/placements')
        self.placement.selected_containers = output_containers
        self.placement.placement_list = output_placement_list
        self.placement.root = self.placement.post()

    @classmethod
    def create(cls, lims, protocol_step, inputs, container_type_name=None, reagent_category=None, **kwargs):
        instance = super(Step, cls)._create(lims, **kwargs)
        # Check configuratio of the step
        if not isinstance(protocol_step, ProtocolStep):
            raise TypeError('protocol_step must be of type ProtocolStep not %s.' % type(protocol_step))
        configuration_node = ElementTree.SubElement(instance.root, 'configuration')
        configuration_node.attrib['uri'] = protocol_step.uri
        configuration_node.text = protocol_step.name

        # Check container name
        # Default to the require type if not provided and only possible choice
        if not container_type_name and len(protocol_step.permittedcontainers) == 1:
            container_type_name = protocol_step.permittedcontainers[0]
        if protocol_step.permittedcontainers and container_type_name in protocol_step.permittedcontainers:
            container_type_node = ElementTree.SubElement(instance.root, 'container-type')
            container_type_node.text = container_type_name
        elif protocol_step.permittedcontainers:
            # TODO: raise early if the container type name is required and missing or not in permitted type
            pass

        # TODO: more work needed to understand how the permitted reagent applies here
        if reagent_category:
            reagent_category_node = ElementTree.SubElement(instance.root, 'reagent_category')
            reagent_category_node.text = reagent_category

        inputs_node = ElementTree.SubElement(instance.root, 'inputs')
        for artifact in inputs:
            if not isinstance(artifact, Artifact):
                raise TypeError('Input must be of type Artifact not %s.' % type(artifact))
            input_node = ElementTree.SubElement(inputs_node, 'input')
            input_node.attrib['uri'] = artifact.uri
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib['uri']
        return instance


class ProtocolStep(Entity):
    """Steps key in the Protocol object"""

    _TAG = 'step'

    name                = StringAttributeDescriptor("name")
    type                = EntityDescriptor('type', Processtype)
    permittedcontainers = StringListDescriptor('container-type', nesting=['permitted-containers'])
    queue_fields        = AttributeListDescriptor('queue-field', nesting=['queue-fields'])
    step_fields         = AttributeListDescriptor('step-field', nesting=['step-fields'])
    sample_fields       = AttributeListDescriptor('sample-field', nesting=['sample-fields'])
    step_properties     = AttributeListDescriptor('step_property', nesting=['step_properties'])
    epp_triggers        = AttributeListDescriptor('epp_trigger', nesting=['epp_triggers'])


class Protocol(Entity):
    """Protocol, holding ProtocolSteps and protocol-properties"""
    _URI = 'configuration/protocols'
    _TAG = 'protocol'

    steps      = EntityListDescriptor('step', ProtocolStep, nesting=['steps'])
    properties = AttributeListDescriptor('protocol-property', nesting=['protocol-properties'])


class Stage(Entity):
    """Holds Protocol/Workflow"""
    name     = StringAttributeDescriptor('name')
    index    = IntegerAttributeDescriptor('index')
    protocol = EntityDescriptor('protocol', Protocol)
    step     = EntityDescriptor('step', ProtocolStep)


class Workflow(Entity):
    """ Workflow, introduced in 3.5"""
    _URI = "configuration/workflows"
    _TAG = "workflow"

    name      = StringAttributeDescriptor("name")
    status    = StringAttributeDescriptor("status")
    protocols = EntityListDescriptor('protocol', Protocol, nesting=['protocols'])
    stages    = EntityListDescriptor('stage', Stage, nesting=['stages'])


class ReagentType(Entity):
    """Reagent Type, usually, indexes for sequencing"""
    _URI = "reagenttypes"
    _TAG = "reagent-type"
    _PREFIX = 'rtp'

    category = StringDescriptor('reagent-category')

    def __init__(self, lims, uri=None, id=None):
        super(ReagentType, self).__init__(lims, uri, id)
        assert self.uri is not None
        self.root = lims.get(self.uri)
        self.sequence = None
        for t in self.root.findall('special-type'):
            if t.attrib.get("name") == "Index":
                for child in t.findall("attribute"):
                    if child.attrib.get("name") == "Sequence":
                        self.sequence = child.attrib.get("value")

class Queue(Entity):
    """Queue of a given step"""
    _URI = "queues"
    _TAG= "queue"
    _PREFIX = "que"

    artifacts = EntityListDescriptor("artifact", Artifact, nesting=["artifacts"])

Sample.artifact          = EntityDescriptor('artifact', Artifact)
StepActions.step         = EntityDescriptor('step', Step)
Stage.workflow           = EntityDescriptor('workflow', Workflow)
Artifact.workflow_stages = EntityListDescriptor(tag='workflow-stage', klass=Stage, nesting=['workflow-stages'])
Step.configuration       = EntityDescriptor('configuration', ProtocolStep)
