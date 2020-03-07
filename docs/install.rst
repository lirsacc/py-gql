.. _installation:

Installation
============

- **Python Versions**: ``py_gql`` supports CPython 3.5 and newer.
- **Platforms**: Unix/Posix, MacOS X.
- **Dependencies**: :mod:`py_gql` has no direct dependency.

Installing from PyPI
--------------------

A source distribution and universal wheel are available on
`PyPI <https://pypi.org/project/py-gql/>`_.

To install, run:

.. code::

    $ pip install py-gql


Cython
~~~~~~

.. warning::

    This is experimental and might be removed in the future. It may also present
    some rough edges.

The default pip install should install the universal wheel, however for some
extra performance in production py-gql's ``setup.py`` can detect the presence
of `Cython <http://cython.org/>`_ and compile (i.e. cythonize) the code in pure
python mode for significant performance improvements. This requires a C compiler
to be available on the system.

To benefit from this, run:

.. code::

    $ PY_GQL_USE_CYTHON=1 pip install --no-binary :all: py-gql

**Notes**

- The code is not written or optimized for Cython i.e. we use the
  `pure python <http://cython.readthedocs.io/en/latest/src/tutorial/pure.html>`_
  compilation mode.
- Setting the ``CYTHON_TRACE`` environment variable will instruct Cython to
  compile with line trace information useful for profiling and debugging.
  See `this document <https://cython.readthedocs.io/en/latest/src/tutorial/profiling_tutorial.html>`_
  for more details.
- You need Xcode Command Line Tools installed on MaxOS X for this to work.


Installing from source
----------------------

py-gql's source code is hosted on `Github <https://github.com/lirsacc/py-gql>`_.

You can install the development version from source after cloning locally:

.. code::

    $ git clone git@github.com:lirsacc/py-gql.git py_gql
    $ cd py-gql
    $ pip install -e .


Or you can directly install through pip `VCS support
<https://pip.pypa.io/en/stable/reference/pip_install/#vcs-support>`_:

.. code::

    $ pip install git+ssh://git@github.com/lirsacc/py-gql.git@master
