Practical Examples
==================

Change value of a UDF of all artifacts of a Step in progress
------------------------------------------------------------

The goal of this example is to show how you could change the value of a UDF named udfname in all input artifacts.
This example assume you have a :py:class:`Lims <pyclarity_lims.lims.Lims>` and a process id.

.. code::

        # Create a process entity from an existing process in the LIMS
        p = Process(l, id=process_id)
        # Retreive  each input artifacts and iterate over them
        for artifact in p.all_inputs():
            # change the value of the udf
            artifact.udf['udfname'] = 'udfvalue'
            # upload the artifact back to the Lims
            artifact.put()

In some cases we want to optimise the number of query sent to the LIMS and make use of the batched query the API offers.

.. code::

        p = Process(l, id=process_id)
        # This time we create all the Artifacts entities and use the batch query to retrieve the content
        # then iterate over them
        for artifact in p.all_inputs(resolve=True):
            artifact.udf['udfname'] = 'udfvalue'
        # Upload all the artifacts in one batch query
        l.batch_put(p.all_inputs())

.. note::

        the batch queries are ususally faster than the equivalent multiple individual queries.
        However the gain seems very variable and is not as high as one might expect.

Find all the samples that went through a Step with a specific udf value
-----------------------------------------------------------------------

This is a typical search that is performed when searching for sample that went through a specific sequencing run.

.. code::

        # there should only be one such process
        processes = l.get_processes(type='Sequencing', udf={'RunId': run_id})
        samples = set()
        for a in processes[0].all_inputs(resolve=True):
            samples.update(a.samples)

.. _up-to-date-program-status:

Make sure to have the up-to-date program status
-----------------------------------------------

Because all the entities are cached, sometime the Entities get out of date especially
when the data in the LIMS  is changing rapidly: like the status of a running program.

.. code::

        s = Step(l, id=step_id)
        s.program_status.status  # returns RUNNING
        sleep(10)
        s.program_status.status  # returns RUNNING because it is still cached
        s.program_status.get(force=True)
        s.program_status.status  # returns COMPLETE

The function :py:func:`get <pyclarity_lims.entities.Entity.get>` is most of the time used implicitly
but can be used explicitly with the force option to bypass the cache and retrieve an up-to-date version of the instance.

Create sample with a Specific udfs
----------------------------------

So far we always retrieve entities from the LIMS and in some case modified them before uploading them back.
We can also create some of these entities and upload them to the LIMS.
Here is how to create a sample with a specific udf.

.. code::

        Sample.create(l, container=c, position='H:3', project=p, name='sampletest', udf={'testudf':'testudf_value'})


Start and complete a new Step from submitted samples
---------------------------------------

Creating a step, filling in the placement and the next actions then completing the step
can be very convenient when you want to automate the execution of part of your workflow.
Here is an example with one sample placed into a tube.

.. code::

        # Retrieve samples/artifact/workflow stage
        samples = l.get_samples(projectname='project1')
        art = samples[0].artifact
        # Find workflow 'workflowname' and take its first stage
        stage = l.get_workflows(name='workflowname')[0].stages[0]

        # Queue the artifacts to the stage
        l.route_artifacts([art], stage_uri=stage.uri)

        # Create a new step from that queued artifact
        s = Step.create(l, protocol_step=stage.step, inputs=[art], container_type_name='Tube')

        # Create the output container
        ct = l.get_container_types(name='Tube')[0]
        c = Container.create(l, type=ct)

        # Retrieve the output artifact that was generated automatically from the input/output map
        output_art = s.details.input_output_maps[0][1]['uri']

        # Place the output artifact in the container
        # Note that the placements is a list of tuple ( A, ( B, C ) )
        # Where A is output artifact, B the output Container and C the location on this container
        output_placement_list=[(output_art, (c, '1:1'))]
        # set_placements creates the placement entity and "put" it
        s.set_placements([c], output_placement_list)

        # Move from "Record detail" window to the "Next Step"
        s.advance()

        # Set the next step
        actions = s.actions.next_actions[0]['action'] = 'complete'
        s.actions.put()

        # Complete the step
        s.advance()