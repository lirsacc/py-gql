.. py-gql documentation master file, created by
   sphinx-quickstart on Sat Jun 16 11:06:30 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to py-gql's documentation!
==================================

**Release:** v\ |version| (:ref:`installation`)

`py-gql </>`_ is a pure python `GraphQL <http://facebook.github.io/graphql/>`_
implementation aimed at creating GraphQL servers. It supports:

- Parsing the GraphQL query language and schema definition language.
- Building a GraphQL type schema programmatically and from Schema Definition
  files (including support for schema directives).
- Validating and executing GraphQL operations against a type schema.

The source code, issue tracker and development guidelines are available on
`Github <https://github.com/lirsacc/py-gql>`_.


Example
-------

.. literalinclude:: ../examples/hello_world.py
   :language: python


GraphQL
-------

GraphQL is a data query language and runtime specification originally developed
at Facebook and released publicly in 2015. It provides semantics for describing
your data as a type schema and exposing them to clients. It is backend agnostic,
which means you can freely choose the transport and serialization protocols,
data storage layer, etc. that fit your project / organization and use GraphQL as
a thin layer on top.

If you are not familiar with GraphQL already, we strongly suggest you head
over to `graphql.org <https://graphql.org>`_ and have a look at the
`official introduction <https://graphql.org/learn/>`_ and `the specification
<https://github.com/facebook/graphql>`_ before going any further.

Documentation
-------------

.. toctree::
    :maxdepth: 3

    install
    usage/index
    api/index
    CHANGES


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
