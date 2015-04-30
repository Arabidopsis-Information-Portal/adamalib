===============================
Adama Library
===============================

`Adamalib` provides a Python library/SDK for interacting with Adama_.
It is designed to be used as a standalone library in the user's local machine to develop Adama microservices.

Installation
============

Use `pip`::

  pip install git+git://github.com/Arabidopsis-Information-Portal/adamalib.git

It'll be moved to PyPI as soon as it reaches some stability.

As an alternative, see `using adamalib in Docker`_  below.


Using adamalib in Docker
========================

This repository includes a ``Dockerfile`` and a ``docker-compose.yml``
file, which allows a zero installation version of ``adamalib``.

The only requirement is Docker_ and `docker-compose`_, most likely
already installed in your system.

Then, clone this repository and execute ``docker-compose`` as follows:

.. code-block:: bash

   $ git clone https://github.com/Arabidopsis-Information-Portal/adamalib.git
   $ cd adamalib
   $ docker-compose build
   $ docker-compose up

(a bug in ``docker-compose`` requires doing the steps ``build`` and ``up`` separately. 
In the future, only ``up`` will be necessary.)

Navigate to http://localhost:8888 and access the Jupyter_ notebook
with password ``adamalib``.  The notebook ``Example.ipynb`` contains a
full example of use.  The notebook ``Provenance.ipynb`` contains an example of
accessing provenance information from Python.

**Note**: If you are running on a Mac with ``boot2docker``, substitute ``localhost`` by 
the output of:

.. code-block:: bash

   $ boot2docker ip


License
=======

Free software: MIT license

.. _Adama: https://github.com/Arabidopsis-Information-Portal/adama
.. _Docker: https://docs.docker.com/installation/#installation
.. _docker-compose: https://docs.docker.com/compose/install/
.. _using adamalib in Docker: https://github.com/Arabidopsis-Information-Portal/adamalib#using-adamalib-in-docker
.. _Jupyter: http://ipython.org/
