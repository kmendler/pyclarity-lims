import random
from pyclarity_lims.entities import *


def _str_representation(value):
    if isinstance(value, list):
        return [_str_representation(v) for v in value]
    if isinstance(value, tuple):
        return [_str_representation(v) for v in value]
    elif isinstance(value, dict):
        return dict([(k, _str_representation(v)) for k, v in value.items()])
    elif value is None:
        return value
    else:
        return repr(value)


def _stringify_and_order(value):
    if isinstance(value, list):
        return str(sorted([_stringify_and_order(v) for v in value]))
    elif isinstance(value, dict):
        return '{' + ', '.join(["%s: %s" % (k, _stringify_and_order(value[k])) for k in sorted(value)]) + '}'
    else:
        return str(value)


class TestEntity:
    properties = None
    functions = None
    klass = None

    def __init__(self, lims, entity_uri, value_dict):
        self.entity = self.klass(lims, uri=entity_uri)
        self.value_dict = value_dict

    def test_properties(self):
        tested_properties = []
        for k in self.value_dict:
            assert k in self.properties
            tested_properties.append(k)
            exp = self.value_dict.get(k)
            obs = _str_representation(getattr(self.entity, k))
            if _stringify_and_order(exp) != _stringify_and_order(obs):
                print('In testing %s comparing %s expected and observed' % (self.klass.__name__, k))
                print('exp: ' + str(exp))
                print('obs: ' + str(obs))

        non_tested_properties = set(self.properties).difference(tested_properties)
        for k in non_tested_properties:
            # only access to make sure nothing crash in the parsing
            getattr(self.entity, k)

    def get_expected_values(self):
        expected_values = {}
        for prop in self.properties:
            value = getattr(self.entity, prop)
            expected_values[prop] = _str_representation(value)
        return expected_values


class TestArtifact(TestEntity):
    properties = ['concentration', 'container', 'files', 'id', 'location', 'name', 'output_type', 'parent_process',
                  'qc_flag', 'reagent_labels', 'samples', 'type', 'udf', 'uri', 'volume',
                  'workflow_stages', 'workflow_stages_and_statuses', 'working_flag']
    functions = ['create', 'input_artifact_list']
    klass = Artifact


class TestSample(TestEntity):
    properties = ['artifact', 'date_completed', 'date_received', 'externalids', 'files', 'id', 'name', 'notes',
                  'project', 'submitter', 'udf', 'udt']
    functions = ['create']
    klass = Sample


class TestProject(TestEntity):
    properties = ['close_date', 'externalids', 'files', 'id', 'invoice_date', 'name', 'open_date', 'researcher', 'udf',
                  'udt']
    functions = ['create']
    klass = Project


class TestContainer(TestEntity):
    properties = ['id', 'name', 'occupied_wells', 'placements', 'state', 'type', 'udf', 'udt']
    functions = ['get_placements', 'create']
    klass = Container


class TestProcess(TestEntity):
    properties = ['date_run', 'files', 'id', 'input_output_maps', 'process_parameter', 'protocol_name', 'step',
                  'technician', 'type', 'udf', 'udt']
    functions = ['create', 'output_containers', 'parent_processes', 'analytes', 'input_per_sample', 'all_inputs',
                 'all_outputs', 'result_files', 'shared_result_files', 'outputs_per_input']
    klass = Process


class TestStep(TestEntity):
        properties = ['actions', 'available_programs', 'configuration', 'current_state', 'date_completed',
                      'date_started', 'details', 'id', 'placements', 'pools', 'process', 'program_names',
                      'program_status', 'reagent_lots']
        functions = ['create', 'advance', 'set_placements', 'trigger_program']
        klass = Step


class TestWorkflow(TestEntity):
        properties = ['name', 'protocols', 'stages', 'status']
        functions = ['create']
        klass = Workflow


class TestProtocol(TestEntity):
        properties = ['id', 'properties', 'steps']
        functions = ['create']
        klass = Protocol


class TestLab(TestEntity):
    properties = ['billing_address', 'externalids', 'id', 'name', 'shipping_address', 'udf', 'udt', 'website']
    functions = ['create']
    klass = Lab


class TestResearcher(TestEntity):
    properties = ['email', 'externalids', 'fax', 'first_name', 'id', 'initials', 'lab', 'last_name', 'name', 'phone',
                  'udf', 'udt']
    functions = ['create']
    klass = Researcher


class TestReagentKit(TestEntity):
    properties = ['archived', 'id', 'name', 'supplier', 'uri', 'website']
    functions = ['create']
    klass = ReagentKit


class TestReagentLot(TestEntity):
    properties = ['created_by', 'created_date', 'expiry_date', 'id', 'last_modified_by', 'last_modified_date',
                  'lot_number', 'name', 'reagent_kit', 'status', 'usage_count']
    functions = ['create']
    klass = ReagentLot


class TestReagentType(TestEntity):
    properties = ['category', 'id', 'sequence']
    functions = ['create']
    klass = ReagentType


class TestStage(TestEntity):
    properties = ['id', 'index', 'name', 'protocol', 'step', 'workflow']
    functions = ['create']
    klass = Stage


class TestProtocolStep(TestEntity):
    properties = ['epp_triggers', 'id', 'name', 'permitted_containers', 'queue_fields', 'sample_fields', 'step_fields',
                  'step_properties', 'type', 'uri']
    functions = ['create']
    klass = ProtocolStep


class TestQueue(TestEntity):
    properties = ['artifacts', 'id', 'queued_artifacts', 'uri']
    functions = ['create']
    klass = Queue


test_classes = [TestArtifact, TestSample, TestProject, TestContainer, TestLab, TestResearcher, TestProcess, TestStep,
                TestWorkflow, TestProtocol, TestReagentKit, TestReagentLot, TestReagentType, TestStage,
                TestProtocolStep, TestQueue]
map_entity_to_test = dict([(test_class.klass, test_class) for test_class in test_classes])


def generate_entities_expected_output(lims):
    """
    This function will extract random entities from the provided lims and dump a string representation in a dict
    """
    def get_x_entities(list_entities, test_class, number, uri_getter=None):
        dict_x_entities = {}
        for ent in random.sample(list_entities, number):
            if uri_getter:
                uri = uri_getter(ent)
            else:
                uri = ent.uri
            test_ent = test_class(lims, uri, None)
            dict_x_entities[uri] = test_ent.get_expected_values()
        return dict_x_entities

    nb = 10  # Number of entities sampled
    expected_values = {}

    expected_values[TestArtifact.klass.__name__] = get_x_entities(lims.get_artifacts(), TestArtifact, nb)
    expected_values[TestSample.klass.__name__] = get_x_entities(lims.get_samples(), TestSample, nb)
    expected_values[TestProject.klass.__name__] = get_x_entities(lims.get_projects(), TestProject, nb)
    expected_values[TestContainer.klass.__name__] = get_x_entities(lims.get_containers(), TestContainer, nb)
    processes = lims.get_processes()
    expected_values[TestProcess.klass.__name__] = get_x_entities(processes, TestProcess, nb)
    # Steps and processes have the same ids
    expected_values[TestStep.klass.__name__] = get_x_entities(processes, TestStep, nb, uri_getter=lambda x: x.step.uri)

    expected_values[TestLab.klass.__name__] = get_x_entities(lims.get_labs(), TestLab, nb)
    expected_values[TestResearcher.klass.__name__] = get_x_entities(lims.get_researchers(), TestResearcher, nb)
    expected_values[TestReagentKit.klass.__name__] = get_x_entities(lims.get_reagent_kits(), TestReagentKit, nb)
    expected_values[TestReagentLot.klass.__name__] = get_x_entities(lims.get_reagent_lots(), TestReagentLot, nb)
    expected_values[TestReagentType.klass.__name__] = get_x_entities(lims.get_reagent_types(), TestReagentType, nb)
    workflows = lims.get_workflows()
    expected_values[TestWorkflow.klass.__name__] = get_x_entities(workflows, TestWorkflow, nb)
    # get all stages from a random set of workflows
    stages = [stage for sublist in random.sample(workflows, nb) for stage in sublist.stages]
    expected_values[TestStage.klass.__name__] = get_x_entities(stages, TestStage, nb)

    protocols = lims.get_protocols()
    expected_values[TestProtocol.klass.__name__] = get_x_entities(protocols, TestProtocol, nb)
    # get all steps from a random set of protocols
    steps = [step for protocol in random.sample(protocols, nb) for step in protocol.steps]
    expected_values[TestProtocolStep.klass.__name__] = get_x_entities(steps, TestProtocolStep, nb)
    expected_values[TestQueue.klass.__name__] = get_x_entities(steps, TestQueue, nb, uri_getter=lambda x: x.queue.uri)

    return expected_values


def test_all_entities(lims, entities_config):
    for entity in map_entity_to_test:
        entity_config = entities_config.get(entity.__name__)
        test_class = map_entity_to_test.get(entity)
        if entity_config:
            for entity_uri in entity_config:
                test = test_class(lims, entity_uri, entity_config.get(entity_uri))
                test.test_properties()
