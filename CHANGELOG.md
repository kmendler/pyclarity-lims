Changelog for Pyclarity-Lims
============================

0.4.7 (2019-02-19)
------------------

- Fix for get_batch return type now return list consistently.
- New option for lims.get_file_content to allow retrieval of binary stream
- Ability to create/add to input-output-maps (useful in testing)

0.4.6 (2019-01-25)
------------------

- New function for creating Samples and Container vi batch query 


0.4.5 (2018-09-14)
------------------

- Fixed bug in Process.outputs_per_input
- Additional tests for Process inputs/outputs


0.4.4 (2018-09-10)
------------------

- Pools can now be created in the `StepPools` entity  
- `Queue` can now return paginated artifact list
- Add nb_page argument to Search function such as `lims.get_samples(nb_page=1)`
- Documentation improvments 
- Add missing `.get` in `Step.advance()`
- Fix future warning in `Step.available_programs` (dbarrell)
- Other minor bug fixes


0.4.3 (2018-02-07)
------------------

- Add rough integration testing facility
- Fixes parsing of time stamp in QueuedArtifactList
- Fixes bug in clear function of muttable descriptor


0.4.2 (2018-01-10)
------------------

- Parse pools in a step as dictionary.
- Fix next action in the Step Action object
- Better parsing of the Queue to retrieve the time artifacts were queued 


0.4.1 (2017-08-04)
------------------

- Add ability to create step with replicates (multiple output artifacts)


0.4 (2017-07-06)
----------------
 - forked genologics repo and rename to pyclarity_lims
 - Add ability to create Step instance from queued artifact to start a new process
 - Add documentation

0.3.12 (2017-02-22)
-------------------
