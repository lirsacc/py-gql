Installation
============

**Release:** v\ |version|

**Python versions**: Python 2.7, 3.5 (untested), 3.6, 3.7

**Platforms**: Unix/Posix

**Dependencies**: `six <https://pypi.org/project/six/>`_, `futures <https://github.com/agronholm/pythonfutures>`_


Installing from PyPi
----------------------------

.. note::
    ``py-gql`` has not been released to PyPi yet.

Installing with Cython
----------------------

.. warning::

    This is experimental and might be removed in the future.

In case `Cython <http://cython.org/>`_ is installed when installing this package
with setuptools, parts of the code will be compiled as C-extensions to bring
performance improvements.

Notes:

- There is not specific Cython code or optimization and we use the
  `pure python <http://cython.readthedocs.io/en/latest/src/tutorial/pure.html>`_
  mode.
- In case you need Cython installed but do not want this package to be
  cythonized, just set the ``CYTHON_DISABLE`` environment variable.
- Setting the ``CYTHON_TRACE`` environment variable will instruct Cython to
  compile with line trace information for profiling. See `this document
  <https://cython.readthedocs.io/en/latest/src/tutorial/profiling_tutorial.html>`_
  for more details.


Installing the development version
----------------------------------

You need git installed for this to work.

.. code::

    git clone git://github.com/lirsacc/py-gql.git
    cd py-gql
    pip install -e .
