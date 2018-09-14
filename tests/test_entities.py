from sys import version_info
from unittest import TestCase
from xml.etree import ElementTree
from pyclarity_lims.entities import ProtocolStep, StepActions, Researcher, Artifact, \
    Step, StepPlacements, Container, Stage, ReagentKit, ReagentLot, Sample, Project, Process
from pyclarity_lims.lims import Lims
from tests import NamedMock, elements_equal
if version_info[0] == 2:
    from mock import patch, Mock
else:
    from unittest.mock import patch, Mock

url = 'http://testgenologics.com:4040'

########
# Entities in XML
generic_artifact_xml = """<?xml version='1.0' encoding='utf-8'?>
<art:artifact xmlns:art="http://genologics.com/ri/artifact"  xmlns:file="http://genologics.com/ri/file" xmlns:udf="http://genologics.com/ri/userdefined"  uri="{url}/api/v2/artifacts/a1" limsid="a1">
<name>test_sample1</name>
<type>Analyte</type>
<output-type>Analyte</output-type>
<qc-flag>PASSED</qc-flag>
<location>
  <container uri="{url}/api/v2/containers/c1" limsid="c1"/>
  <value>A:1</value>
</location>
<working-flag>true</working-flag>
<sample uri="{url}/api/v2/samples/s1" limsid="s1"/>
<udf:field type="Numeric" name="Ave. Conc. (ng/uL)">1</udf:field>
<udf:field type="String" name="Workflow Desired">TruSeq Nano DNA Sample Prep</udf:field>
<workflow-stages>
<workflow-stage status="QUEUED" name="Test workflow s2" uri="{url}/api/v2/configuration/workflows/1/stages/2"/>
<workflow-stage status="COMPLETE" name="Test workflow s1" uri="{url}/api/v2/configuration/workflows/1/stages/1"/>
</workflow-stages>
</art:artifact>"""

generic_step_placements_xml = """<?xml version='1.0' encoding='utf-8'?>
<stp:placements xmlns:stp="http://genologics.com/ri/step" uri="{url}/steps/s1/placements">
  <step uri="{url}/steps/s1" />
  <configuration uri="{url}/configuration/protocols/1/steps/1">Step name</configuration>
  <selected-containers>
    <container uri="{url}/containers/{container}" />
  </selected-containers>
  <output-placements>
    <output-placement uri="{url}/artifacts/a1">
      <location>
        <container limsid="{container}" uri="{url}/containers/{container}" />
        <value>{loc1}</value>
      </location>
    </output-placement>
    <output-placement uri="{url}/artifacts/a2">
      <location>
        <container limsid="{container}" uri="{url}/containers/{container}" />
        <value>{loc2}</value>
      </location>
    </output-placement>
  </output-placements>
</stp:placements>"""

generic_reagentkit_xml = """<?xml version='1.0' encoding='utf-8'?>
<kit:reagent-kit xmlns:kit="http://genologics.com/ri/reagentkit" uri="{url}:8080/api/v2/reagentkits/r1">
<name>regaentkitname</name>
<supplier>reagentProvider</supplier>
<website>www.reagentprovider.com</website>
<archived>false</archived>
</kit:reagent-kit>"""

generic_reagentlot_xml = """<?xml version='1.0' encoding='utf-8'?>
<lot:reagent-lot xmlns:lot="http://genologics.com/ri/reagentlot" limsid="l1" uri="{url}/api/v2/reagentlots/l1">
<reagent-kit uri="{url}/api/v2/reagentkits/r1" name="kitname"/>
<name>kitname</name>
<lot-number>100</lot-number>
<created-date>2015-07-16</created-date>
<last-modified-date>2015-08-17</last-modified-date>
<expiry-date>2022-08-16</expiry-date>
<created-by uri="{url}/api/v2/researchers/1"/>
<last-modified-by uri="{url}/api/v2/researchers/1"/>
<status>ARCHIVED</status>
<usage-count>1</usage-count>
</lot:reagent-lot>"""

generic_step = """<?xml version='1.0' encoding='utf-8'?>
<stp:step xmlns:stp="http://genologics.com/ri/step" current-state="Completed" limsid="{stepid}" uri="{url}/api/v2/steps/{stepid}">
<configuration uri="{url}/api/v2/configuration/protocols/p1/steps/p1s1">My fancy protocol</configuration>
<date-started>2016-11-22T10:43:32.857+00:00</date-started>
<date-completed>2016-11-22T14:31:14.100+00:00</date-completed>
<actions uri="{url}/api/v2/steps/{stepid}/actions"/>
<placements uri="{url}/api/v2/steps/{stepid}/placements"/>
<program-status uri="{url}/api/v2/steps/{stepid}/programstatus"/>
<details uri="{url}/api/v2/steps/{stepid}/details"/>
<available-programs>
<available-program name="program1" uri="{url}/api/v2/steps/{stepid}/trigger/t1"/>
<available-program name="program2" uri="{url}/api/v2/steps/{stepid}/trigger/t2"/>
</available-programs>
</stp:step>"""

generic_step_program_status = """<?xml version='1.0' encoding='utf-8'?>
<stp:program-status xmlns:stp="http://genologics.com/ri/step" uri="{url}/api/v2/steps/{stepid}/programstatus">
<step uri="{url}/api/v2/steps/{stepid}" rel="steps"/>
<configuration uri="{url}/api/v2/configuration/protocols/p1/steps/p1s1">My fancy protocol</configuration>
<status>ERROR</status>
<message>Traceback Error message</message>
</stp:program-status>"""

generic_step_actions_xml = """<stp:actions xmlns:stp="http://genologics.com/ri/step" uri="...">
  <step rel="..." uri="{url}/steps/s1">
  </step>
  <configuration uri="{url}/config/1">...</configuration>
  <next-actions>
    <next-action artifact-uri="{url}/artifacts/a1" action="requeue" step-uri="..." rework-step-uri="...">
    </next-action>
  </next-actions>
  <escalation>
    <request>
      <author uri="{url}/researchers/r1">
        <first-name>foo</first-name>
        <last-name>bar</last-name>
      </author>
      <reviewer uri="{url}/researchers/r1">
        <first-name>foo</first-name>
        <last-name>bar</last-name>
      </reviewer>
      <date>01-01-1970</date>
      <comment>no comments</comment>
    </request>
    <review>
      <author uri="{url}/researchers/r1">
        <first-name>foo</first-name>
        <last-name>bar</last-name>
      </author>
      <date>01-01-1970</date>
      <comment>no comments</comment>
    </review>
    <escalated-artifacts>
      <escalated-artifact uri="{url}/artifacts/r1">
      </escalated-artifact>
    </escalated-artifacts>
  </escalation>
</stp:actions>"""

generic_step_actions_no_escalation_xml = """<stp:actions xmlns:stp="http://genologics.com/ri/step" uri="...">
  <step rel="..." uri="{url}/steps/s1">
  </step>
  <configuration uri="{url}/config/1">...</configuration>
  <next-actions>
    <next-action artifact-uri="{url}/artifacts/a1" action="requeue" step-uri="{url}/steps/s1" rework-step-uri="{url}/steps/s2">
    </next-action>
  </next-actions>
</stp:actions>"""

generic_sample_creation_xml = """
<smp:samplecreation xmlns:smp="http://genologics.com/ri/sample" limsid="s1" uri="{url}/api/v2/samples/s1">
  <location>
    <container limsid="cont1" uri="{url}/api/v2/containers/cont1">
    </container>
    <value>1:1</value>
  </location>
  <name>
    sample1
  </name>
  <project uri="{url}/api/v2/projects/p1" limsid="p1">
  </project>
</smp:samplecreation>
"""

generic_process_xml = """
<prc:process xmlns:udf="http://genologics.com/ri/userdefined" xmlns:file="http://genologics.com/ri/file" xmlns:prc="http://genologics.com/ri/process" uri="{url}/api/v2/processes/p2" limsid="p2">
<type uri="{url}/api/v2/processtypes/pt1">Step Name 5.0</type>
<date-run>2018-06-12</date-run>
<technician uri="{url}/api/v2/researchers/1">
<first-name>Bob</first-name>
<last-name>Marley</last-name>
</technician>
<input-output-map>
<input post-process-uri="{url}/api/v2/artifacts/a1" uri="{url}/api/v2/artifacts/a1" limsid="a1">
<parent-process uri="{url}/api/v2/processes/p1" limsid="p1"/>
</input>
<output uri="{url}/api/v2/artifacts/ao1" output-generation-type="PerAllInputs" output-type="ResultFile" limsid="ao1"/>
</input-output-map>
<input-output-map>
<input post-process-uri="{url}/api/v2/artifacts/a2" uri="{url}/api/v2/artifacts/a2" limsid="a2">
<parent-process uri="{url}/api/v2/processes/p1" limsid="p1"/>
</input>
<output uri="{url}/api/v2/artifacts/ao1" output-generation-type="PerAllInputs" output-type="ResultFile" limsid="ao1"/>
</input-output-map>
<input-output-map>
<input post-process-uri="{url}/api/v2/artifacts/a1" uri="{url}/api/v2/artifacts/a1" limsid="a1">
<parent-process uri="{url}/api/v2/processes/p1" limsid="p1"/>
</input>
<output uri="{url}/api/v2/artifacts/ao2" output-generation-type="PerInput" output-type="ResultFile" limsid="ao2"/>
</input-output-map>
<input-output-map>
<input post-process-uri="{url}/api/v2/artifacts/a2" uri="{url}/api/v2/artifacts/a2" limsid="a2">
<parent-process uri="{url}/api/v2/processes/p1" limsid="p1"/>
</input>
<output uri="{url}/api/v2/artifacts/ao3" output-generation-type="PerInput" output-type="ResultFile" limsid="ao3"/>
</input-output-map>
<udf:field type="Numeric" name="Count">15</udf:field>
<process-parameter name="parameter1"/>
</prc:process>
"""


class TestEntities(TestCase):
    dummy_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <dummy></dummy>"""

    def setUp(self):
        self.lims = Lims(url, username='test', password='password')

    def _tostring(self, entity):
        return self.lims.tostring(ElementTree.ElementTree(entity.root)).decode("utf-8")


class TestStepActions(TestEntities):
    step_actions_xml = generic_step_actions_xml.format(url=url)
    step_actions_no_escalation_xml = generic_step_actions_no_escalation_xml.format(url=url)

    def test_escalation(self):
        s = StepActions(uri=self.lims.get_uri('steps', 'step_id', 'actions'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.step_actions_xml, status_code=200)):
            with patch('requests.post', return_value=Mock(content=self.dummy_xml, status_code=200)):
                r = Researcher(uri='http://testgenologics.com:4040/researchers/r1', lims=self.lims)
                a = Artifact(uri='http://testgenologics.com:4040/artifacts/r1', lims=self.lims)
                expected_escalation = {
                    'status': 'Reviewed',
                    'author': r,
                    'artifacts': [a], 'request': 'no comments',
                    'answer': 'no comments',
                    'reviewer': r}

                assert s.escalation == expected_escalation

    def test_next_actions(self):
        s = StepActions(uri=self.lims.get_uri('steps', 'step_id', 'actions'), lims=self.lims)
        with patch('requests.Session.get',
                   return_value=Mock(content=self.step_actions_no_escalation_xml, status_code=200)):
            step1 = Step(self.lims, uri='http://testgenologics.com:4040/steps/s1')
            step2 = Step(self.lims, uri='http://testgenologics.com:4040/steps/s2')
            artifact = Artifact(self.lims, uri='http://testgenologics.com:4040/artifacts/a1')

            expected_next_actions = [{'artifact': artifact, 'action': 'requeue',
                                      'step': step1, 'rework-step': step2}]
            assert s.next_actions == expected_next_actions


class TestStepPlacements(TestEntities):
    original_step_placements_xml = generic_step_placements_xml.format(url=url, container="c1", loc1='1:1', loc2='2:1')
    modloc_step_placements_xml = generic_step_placements_xml.format(url=url, container="c1", loc1='3:1', loc2='4:1')
    modcont_step_placements_xml = generic_step_placements_xml.format(url=url, container="c2", loc1='1:1', loc2='1:1')

    def test_get_placements_list(self):
        s = StepPlacements(uri=self.lims.get_uri('steps', 's1', 'placements'), lims=self.lims)
        with patch('requests.Session.get',
                   return_value=Mock(content=self.original_step_placements_xml, status_code=200)):
            a1 = Artifact(uri='http://testgenologics.com:4040/artifacts/a1', lims=self.lims)
            a2 = Artifact(uri='http://testgenologics.com:4040/artifacts/a2', lims=self.lims)
            c1 = Container(uri='http://testgenologics.com:4040/containers/c1', lims=self.lims)
            expected_placements = [(a1, (c1, '1:1')), (a2, (c1, '2:1'))]
            assert s.get_placement_list() == expected_placements

    def test_set_placements_list(self):
        a1 = Artifact(uri='http://testgenologics.com:4040/artifacts/a1', lims=self.lims)
        a2 = Artifact(uri='http://testgenologics.com:4040/artifacts/a2', lims=self.lims)
        c1 = Container(uri='http://testgenologics.com:4040/containers/c1', lims=self.lims)

        s = StepPlacements(uri=self.lims.get_uri('steps', 's1', 'placements'), lims=self.lims)
        with patch('requests.Session.get',
                   return_value=Mock(content=self.original_step_placements_xml, status_code=200)):
            new_placements = [(a1, (c1, '3:1')), (a2, (c1, '4:1'))]
            s.placement_list = new_placements
            assert elements_equal(s.root, ElementTree.fromstring(self.modloc_step_placements_xml))

    def test_set_placements_list_fail(self):
        a1 = Artifact(uri='http://testgenologics.com:4040/artifacts/a1', lims=self.lims)
        a2 = Artifact(uri='http://testgenologics.com:4040/artifacts/a2', lims=self.lims)
        c2 = Container(uri='http://testgenologics.com:4040/containers/c2', lims=self.lims)

        s = StepPlacements(uri=self.lims.get_uri('steps', 's1', 'placements'), lims=self.lims)
        with patch('requests.Session.get',
                   return_value=Mock(content=self.original_step_placements_xml, status_code=200)):
            new_placements = [(a1, (c2, '1:1')), (a2, (c2, '1:1'))]
            s.placement_list = new_placements
            assert elements_equal(s.root, ElementTree.fromstring(self.modcont_step_placements_xml))


class TestStep(TestEntities):
    step_xml = generic_step.format(url=url, stepid='s1')
    step_prog_status = generic_step_program_status.format(url=url, stepid='s1')

    def test_create(self):
        inputs = [
            Mock(spec=Artifact, lims=self.lims, uri='http://testgenologics.com:4040/api/v2/artifacts/a1'),
            Mock(spec=Artifact, lims=self.lims, uri='http://testgenologics.com:4040/api/v2/artifacts/a2')
        ]
        protocol_step = NamedMock(
            spec=ProtocolStep,
            real_name='My fancy step',
            uri='http://testgenologics.com:4040/api/v2/configuration//protocols/p1/steps/p1s1',
            permitted_containers=['Tube']
        )
        with patch('pyclarity_lims.lims.requests.post',
                   return_value=Mock(content=self.step_xml, status_code=201)) as patch_post:
            Step.create(self.lims, protocol_step=protocol_step, inputs=inputs, replicates=[1, 2])
            data = '''<?xml version='1.0' encoding='utf-8'?>
            <stp:step-creation xmlns:stp="http://genologics.com/ri/step">
                <configuration uri="http://testgenologics.com:4040/api/v2/configuration//protocols/p1/steps/p1s1">
                    My fancy step
                </configuration>
                <container-type>Tube</container-type>
                <inputs>
                    <input uri="http://testgenologics.com:4040/api/v2/artifacts/a1" replicates="1"/>
                    <input uri="http://testgenologics.com:4040/api/v2/artifacts/a2" replicates="2"/>
                </inputs>
            </stp:step-creation>
            '''
            assert elements_equal(ElementTree.fromstring(patch_post.call_args_list[0][1]['data']), ElementTree.fromstring(data))

    def test_create2(self):
        inputs = [
            Mock(spec=Artifact, lims=self.lims, uri='http://testgenologics.com:4040/api/v2/artifacts/a1'),
            Mock(spec=Artifact, lims=self.lims, uri='http://testgenologics.com:4040/api/v2/artifacts/a2')
        ]
        protocol_step = NamedMock(
            spec=ProtocolStep,
            real_name='My fancy step',
            uri='http://testgenologics.com:4040/api/v2/configuration//protocols/p1/steps/p1s1',
            permitted_containers=['Tube']
        )
        with patch('pyclarity_lims.lims.requests.post',
                   return_value=Mock(content=self.step_xml, status_code=201)) as patch_post:
            # replicates default to 1
            Step.create(self.lims, protocol_step=protocol_step, inputs=inputs)
            data = '''<?xml version='1.0' encoding='utf-8'?>
            <stp:step-creation xmlns:stp="http://genologics.com/ri/step">
                <configuration uri="http://testgenologics.com:4040/api/v2/configuration//protocols/p1/steps/p1s1">
                    My fancy step
                </configuration>
                <container-type>Tube</container-type>
                <inputs>
                    <input uri="http://testgenologics.com:4040/api/v2/artifacts/a1" replicates="1"/>
                    <input uri="http://testgenologics.com:4040/api/v2/artifacts/a2" replicates="1"/>
                </inputs>
            </stp:step-creation>
            '''
            assert elements_equal(ElementTree.fromstring(patch_post.call_args_list[0][1]['data']), ElementTree.fromstring(data))

    def test_parse_entity(self):
        with patch('requests.Session.get', return_value=Mock(content=self.step_xml, status_code=200)):
            s = Step(self.lims, id='s1')
            s.get()
        assert [p[0] for p in s.available_programs] == ['program1', 'program2']
        assert s.date_started == '2016-11-22T10:43:32.857+00:00'
        assert s.date_completed == '2016-11-22T14:31:14.100+00:00'
        assert s.current_state == 'Completed'
        assert s.actions.uri == 'http://testgenologics.com:4040/api/v2/steps/s1/actions'
        assert s.details.uri == 'http://testgenologics.com:4040/api/v2/steps/s1/details'
        assert s.placements.uri == 'http://testgenologics.com:4040/api/v2/steps/s1/placements'
        assert s.program_status.uri == 'http://testgenologics.com:4040/api/v2/steps/s1/programstatus'
        assert s.program_names == ['program1', 'program2']

    def test_trigger_program(self):
        with patch('requests.Session.get', return_value=Mock(content=self.step_xml, status_code=200)):
            s = Step(self.lims, id='s1')
            s.get()
        with patch('pyclarity_lims.lims.requests.post',
                   return_value=Mock(content=self.step_prog_status, status_code=201)):
            prog_status = s.trigger_program('program1')
            assert prog_status.message == 'Traceback Error message'
            assert prog_status.status == 'ERROR'

    def test_advance(self):
        with patch('requests.Session.get', return_value=Mock(content=self.step_xml, status_code=200)):
            with patch('pyclarity_lims.lims.requests.post', return_value=Mock(content=self.step_xml, status_code=201)) as patch_post:
                s = Step(self.lims, id='s1')
                s.advance()
                assert elements_equal(ElementTree.fromstring(patch_post.call_args_list[0][1]['data']), ElementTree.fromstring(self.step_xml))


class TestArtifacts(TestEntities):
    root_artifact_xml = generic_artifact_xml.format(url=url)

    def test_input_artifact_list(self):
        a = Artifact(uri=self.lims.get_uri('artifacts', 'a1'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.root_artifact_xml, status_code=200)):
            assert a.input_artifact_list() == []

    def test_workflow_stages_and_statuses(self):
        a = Artifact(uri=self.lims.get_uri('artifacts', 'a1'), lims=self.lims)
        expected_wf_stage = [
            (Stage(self.lims, uri=url + '/api/v2/configuration/workflows/1/stages/2'), 'QUEUED', 'Test workflow s2'),
            (Stage(self.lims, uri=url + '/api/v2/configuration/workflows/1/stages/1'), 'COMPLETE', 'Test workflow s1')
        ]
        with patch('requests.Session.get', return_value=Mock(content=self.root_artifact_xml, status_code=200)):
            assert a.workflow_stages_and_statuses == expected_wf_stage


class TestReagentKits(TestEntities):
    url = 'http://testgenologics.com:4040'
    reagentkit_xml = generic_reagentkit_xml.format(url=url)

    def test_parse_entity(self):
        r = ReagentKit(uri=self.lims.get_uri('reagentkits', 'r1'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.reagentkit_xml, status_code=200)):
            assert r.name == 'regaentkitname'
            assert r.supplier == 'reagentProvider'
            assert r.website == 'www.reagentprovider.com'
            assert r.archived is False

    def test_create_entity(self):
        with patch('pyclarity_lims.lims.requests.post', return_value=Mock(content=self.reagentkit_xml, status_code=201)):
            ReagentKit.create(self.lims, name='regaentkitname', supplier='reagentProvider',
                              website='www.reagentprovider.com', archived=False)
        self.assertRaises(TypeError, ReagentKit.create, self.lims, error='test')


class TestReagentLots(TestEntities):
    reagentlot_xml = generic_reagentlot_xml.format(url=url)
    reagentkit_xml = generic_reagentkit_xml.format(url=url)

    def test_parse_entity(self):
        l = ReagentLot(uri=self.lims.get_uri('reagentkits', 'r1'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.reagentlot_xml, status_code=200)):
            assert l.uri
            assert l.name == 'kitname'
            assert l.lot_number == '100'
            assert l.status == 'ARCHIVED'

    def test_create_entity(self):
        with patch('requests.Session.get', return_value=Mock(content=self.reagentkit_xml, status_code=200)):
            r = ReagentKit(uri=self.lims.get_uri('reagentkits', 'r1'), lims=self.lims)
        with patch('pyclarity_lims.lims.requests.post',
                   return_value=Mock(content=self.reagentlot_xml, status_code=201)):
            l = ReagentLot.create(
                    self.lims,
                    reagent_kit=r,
                    name='kitname',
                    lot_number='100',
                    expiry_date='2020-05-01',
                    status='ACTIVE'
            )
            assert l.uri
            assert l.name == 'kitname'
            assert l.lot_number == '100'


class TestSample(TestEntities):
    sample_creation = generic_sample_creation_xml.format(url=url)

    def test_create_entity(self):
        with patch('pyclarity_lims.lims.requests.post',
                   return_value=Mock(content=self.sample_creation, status_code=201)) as patch_post:
            Sample.create(
                self.lims,
                project=Project(self.lims, uri='project'),
                container=Container(self.lims, uri='container'),
                position='1:1',
                name='s1',
                udf={'test1': 'test1value'}
            )
            data = '''<?xml version=\'1.0\' encoding=\'utf-8\'?>
            <smp:samplecreation xmlns:smp="http://genologics.com/ri/sample" xmlns:udf="http://genologics.com/ri/userdefined">
            <name>s1</name>
            <project uri="project" />
            <location>
              <container uri="container" />
              <value>1:1</value>
            </location>
            <udf:field name="test1" type="String">test1value</udf:field>
            </smp:samplecreation>'''
            print(patch_post.call_args_list[0][1]['data'])
            assert elements_equal(ElementTree.fromstring(patch_post.call_args_list[0][1]['data']), ElementTree.fromstring(data))


class TestProcess(TestEntities):
    process_xml = generic_process_xml.format(url=url)

    def test_result_files(self):
        p = Process(uri=self.lims.get_uri('processes', 'p2'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.process_xml, status_code=200)):
            assert len(p.result_files()) == 3
            assert len(p.result_files(output_generation_type='PerAllInputs')) == 1
            assert len(p.result_files(output_generation_type='PerInput')) == 2

    def test_outputs_per_input(self):
        p = Process(uri=self.lims.get_uri('processes', 'p2'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.process_xml, status_code=200)):
            outputs = [Artifact(self.lims, id='ao1'), Artifact(self.lims, id='ao2')]
            assert p.outputs_per_input('a1') == outputs
            assert p.outputs_per_input(Artifact(self.lims, id='a1')) == outputs
            assert p.outputs_per_input('a1', ResultFile=True) == outputs
            assert p.outputs_per_input('a1', SharedResultFile=True) == []
            assert p.outputs_per_input('a1', Analyte=True) == []

    def test_input_per_sample(self):
        p = Process(uri=self.lims.get_uri('processes', 'p2'), lims=self.lims)
        art1 = Mock(samples=[NamedMock(real_name='s1')])
        art2 = Mock(samples=[NamedMock(real_name='s2')])
        with patch.object(Process, 'all_inputs', return_value=[art1, art2]):
            assert p.input_per_sample('s1') == [art1]

    def test_all_inputs(self):
        p = Process(uri=self.lims.get_uri('processes', 'p2'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.process_xml, status_code=200)):
            inputs = [Artifact(self.lims, id='a1'), Artifact(self.lims, id='a2')]
            assert sorted(p.all_inputs(), key=lambda x: x.id) == inputs

    def test_all_output(self):
        p = Process(uri=self.lims.get_uri('processes', 'p2'), lims=self.lims)
        with patch('requests.Session.get', return_value=Mock(content=self.process_xml, status_code=200)):
            outputs = [Artifact(self.lims, id='ao1'), Artifact(self.lims, id='ao2'), Artifact(self.lims, id='ao3')]
            assert sorted(p.all_outputs(), key=lambda x: x.id) == outputs


