Practical Examples
==================

Change value of a UDF of all artifacts of a Step in progress
------------------------------------------------------------

The goal of this example is to show how you can change the value of a UDF named udfname in all input artifacts.
This example assumes you have a :py:class:`Lims <pyclarity_lims.lims.Lims>` and a process id.

.. code::

        # Create a process entity from an existing process in the LIMS
        p = Process(l, id=process_id)
        # Retreive  each input artifacts and iterate over them
        for artifact in p.all_inputs():
            # change the value of the udf
            artifact.udf['udfname'] = 'udfvalue'
            # upload the artifact back to the Lims
            artifact.put()

In some cases we want to optimise the number of queries sent to the LIMS and make use of the batched query the API offers.

.. code::

        p = Process(l, id=process_id)
        # This time we create all the Artifact entities and use the batch query to retrieve the content
        # then iterate over them
        for artifact in p.all_inputs(resolve=True):
            artifact.udf['udfname'] = 'udfvalue'
        # Upload all the artifacts in one batch query
        l.batch_put(p.all_inputs())

.. note::

        A batch query is usually faster than the equivalent number of individual queries.
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
when the data in the LIMS is changing rapidly, like the status of a running program.

.. code::

        s = Step(l, id=step_id)
        s.program_status.status  # returns RUNNING
        sleep(10)
        s.program_status.status  # returns RUNNING because it is still cached
        s.program_status.get(force=True)
        s.program_status.status  # returns COMPLETE

The function :py:func:`get <pyclarity_lims.entities.Entity.get>` is most of the time used implicitly
but can be used explicitly with the force option to bypass the cache and retrieve an up-to-date version of the instance.

.. _create-sample:

Create sample with a Specific udfs
----------------------------------

So far we have only retrieved entities from the LIMS and in some case modified them before uploading them back.
We can also create some of these entities and upload them to the LIMS.
Here is how to create a sample with a specific udf.

.. code::

        Sample.create(l, container=c, position='H:3', project=p, name='sampletest', udf={'testudf':'testudf_value'})


Start and complete a new Step from submitted samples
----------------------------------------------------

Creating a step, filling in the placements and the next actions, then completing the step
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
        # Note that the placements is a list of tuples ( A, ( B, C ) ), where A is the output artifact,
        # B is the output Container and C is the location on this container
        output_placement_list=[(output_art, (c, '1:1'))]
        # set_placements creates the placement entity and "put"s it
        s.set_placements([c], output_placement_list)

        # Move from "Record detail" window to the "Next Step"
        s.advance()

        # Set the next step
        actions = s.actions.next_actions[0]['action'] = 'complete'
        s.actions.put()

        # Complete the step
        s.advance()


Mix samples in a pool using the api
-----------------------------------

Some step will allow you to mix multiple input :py:class:`artifacts <pyclarity_lims.entities.Artifact>` into a pool also
represented by an :py:class:`artifact <pyclarity_lims.entities.Artifact>`. This can be performed using the
:py:class:`StepPools <pyclarity_lims.entities.StepPools>` entities.

Because the pool :py:class:`artifact <pyclarity_lims.entities.Artifact>` needs to be created in the LIMS, we only
need to provide the pool name and we need to provide `None` in place of the pool

.. code::

        # Assuming a Step in the pooling stage
        s = Step(l, id='122-12345')
        # This provides a list of all the artifacts available to pool
        s.pools.available_inputs
        # The pooled_inputs is a dict where the key is the name of the pool
        # the value is a Tuple with first element is the pool artifact and the second if the pooled input
        # here we're not specifying the pool and will let the LIMS create it.
        s.pools.pooled_inputs['Pool1'] = (None, tuple(s.pools.available_inputs))
        # then upload
        s.pools.put()
        # There no more input artifacts available
        assert s.pools.available_inputs == []
        # There is a pool artifact created
        assert type(s.pools.pooled_inputs['Pool1'][0]).__name__ == 'Artifact'

        # Now we can advance the step
        s.advance()


Creating large number of Samples with create_batch
--------------------------------------------------

We have already seen that you can create sample in :ref:`create-sample`. But when you need to create a
large number of samples, this method can be quite slow. The function
:py:func:`create_batch <pyclarity_lims.lims.Lims.create_batch>` can create multiple samples (or containers) in a single
query. You'll need to specify the Entity you wish to create and the parameters you would have passed to the create
method as one dictionary for each entity to create. The function returns the list of created entity in the same order
as the list of dictionary provided.

.. code::

        # Assuming the Container c and the Project p exists.
        samples = l.create_batch(
            Sample,
            [
                {'container': c, 'project': p, 'name': 'sampletest1', 'position': 'H:1', 'udf':{'testudf': 'testudf_value1'}},
                {'container': c, 'project': p, 'name': 'sampletest2', 'position': 'H:2', 'udf':{'testudf': 'testudf_value2'}},
                {'container': c, 'project': p, 'name': 'sampletest3', 'position': 'H:3', 'udf':{'testudf': 'testudf_value3'}},
                {'container': c, 'project': p, 'name': 'sampletest4', 'position': 'H:4', 'udf':{'testudf': 'testudf_value4'}},
                {'container': c, 'project': p, 'name': 'sampletest5', 'position': 'H:5', 'udf':{'testudf': 'testudf_value5'}}
            ]
        )

.. warning::
   The create_batch function returns entities already created with all attributes specified during the
   creation populated. However it does not include attributes created on the LIMS side such as the artifact of samples.
   These have to be retrieved manually using :py:func:`sample.get(force=True) <pyclarity_lims.entities.Entity.get>`
   or :py:func:`lims.get_batch(samples, force=True) <pyclarity_lims.lims.Lims.get_batch>`

.. code::

        # After creation of the samples above
        samples[0].artifact           # returns None
        samples[0].get(force=True)    # retrieve the attribute as they are on the LIMS
        samples[0].artifact           # returns Artifact(uri=...)
