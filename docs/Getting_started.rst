
Getting started
===============

pyclarity-lims is a module that will help you access your `Basespace-clarity <https://www.genologics.com/clarity-lims/>`_ REST API by parsing the xml the API returns into Python objects.

Lims connection
---------------

To create a Lims connection you'll need to create a :py:class:`Lims <pyclarity_lims.lims.Lims>` object.

.. code::

        from pyclarity_lims.lims import Lims

        l = Lims('https://claritylims.example.com', 'username' , 'Pa55w0rd')

The :py:class:`Lims <pyclarity_lims.lims.Lims>` instance is the main object that will interact with the REST API and manage all communications.
There are two way of accessing information stored in the LIMS:

Searching the Lims
------------------
The most common way of accessing data from the LIMS is to first perform searches. For example, retrieving all samples from project1 would be:

.. code::

        samples = l.get_samples(projectname='project1')

This will return a list of all :py:class:`Sample <pyclarity_lims.entities.Sample>` objects that belong to project1.

The functions from pyclarity_lims closely match the API search function from Basespace-clarity REST API. For example
:py:func:`get_samples <pyclarity_lims.lims.Lims.get_samples>` has similar parameters as the
`samples end point <https://www.genologics.com/files/permanent/API/latest/rest.version.samples.html>`_ from Basespace-clarity

Retrieving object with their id
-------------------------------
In some cases you will know the id or uri of the instance you want to retrieve. In this case you can create the object directly.

Note that you will still need the :py:class:`Lims <pyclarity_lims.lims.Lims>` instance as an argument.

For Example:

.. code::

        from pyclarity_lims.entities import Sample
        sample = Sample(l, id='sample_luid')
        print(sample.name)

Lazy loading and caching
------------------------
All entities such as :py:class:`Sample <pyclarity_lims.entities.Sample>`,
:py:class:`Artifact <pyclarity_lims.entities.Artifact>` or
:py:class:`Step <pyclarity_lims.entities.Step>` are loaded lazily which mean that no query will be sent to the REST API
until an attribute of the object is accessed or a method is run.
In the code above:

.. code::

        from pyclarity_lims.entities import Sample
        sample = Sample(l, id='sample_luid')
        # the Sample object has been created but no query have been sent yet
        print(sample.name)
        # accessing the name of the sample triggers the query

To avoid sending too many queries, all Entities that have been retrieved are also cached which means that once the Entity is retrieved it won't be queried again unless forced.
This makes pyclarity_lims more efficient but also not very well suited for long running process during which the state of the LIMS is likely to change.
You can bypass the cache as shown in :ref:`up-to-date-program-status`.

Looking beyond
--------------
You can look at some :doc:`PracticalExamples`
There are many other search methods available in the :py:class:`Lims <pyclarity_lims.lims.Lims>` and
you can also look at all the classes defined in :doc:`entities`