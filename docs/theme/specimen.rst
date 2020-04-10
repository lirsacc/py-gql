Specimen
========

This is a demo of reStructuredText and Sphinx features and demonstrates styling
of various elements.

.. contents:: Local table of contents

(The above ToC triggers anchors around all page headings beyond what Sphinx
does.)


Body copy and inline markup
---------------------------

The *quick* brown **fox** jumps ``over`` :superscript:`the` lazy
:subscript:`dog`. :title-reference:`Title reference.` Inline linkes like
https://google.com should work too.

References & footnotes
----------------------

.. rubric:: References

Lorem ipsum [Ref]_ dolor sit amet.

.. [Ref] Book or article reference, URL or whatever.

Lorem ipsum [#f1]_ dolor sit amet ... [#f2]_

.. rubric:: Footnotes

.. [#f1] Text of the first footnote.
.. [#f2] Text of the second footno

Headings (2nd level)
--------------------

The 3rd level
~~~~~~~~~~~~~

The 4th level
^^^^^^^^^^^^^

The 5th level
'''''''''''''

Lists
-----

* Bulleted list
* with two items

#. Numbered list
#. with
#. three items

* Nested

  #. List

     * Hooray
     * Hooray
     * Hooray
     * Hooray

  #. List

     * Hooray
     * Hooray
     * Hooray
     * Hooray

* Nested

  #. List

Definition list
~~~~~~~~~~~~~~~

term (up to a line of text)
   Definition of the term, which must be indented

   and can even consist of multiple paragraphs

next term
   Description

Options Lists
~~~~~~~~~~~~~

-a            command-line option "a"
-b file       options can have arguments
              and long descriptions
--long        options can be long also
--input=file  long options can also have
              arguments
/V            DOS/VMS-style options too

Blocks
------

Epigraph
~~~~~~~~

.. epigraph::

  No matter where you go, there you are.

  -- Buckaroo Banzai

Compound paragraph
~~~~~~~~~~~~~~~~~~

.. compound::

   This is a compound paragraph. The 'rm' command is very dangerous.  If you
   are logged in as root and enter ::

       cd /
       rm -rf *

   you will erase the entire contents of your file system.

Topic
~~~~~

.. topic:: Topic

  A topic is like a block quote with a title, or a self-contained section with
  no subsections. Use the "topic" directive to indicate a self-contained idea
  that is separate from the flow of the document. Topics may occur anywhere a
  section or transition may occur. Body elements and topics may not contain
  nested topics.

Raw HTML
~~~~~~~~

.. raw:: html

  <span style="color: red;">This is some raw HTML.</span>


Rubric
~~~~~~

.. rubric:: A paragraph heading that is not used to create a TOC node

Admonitions
-----------

.. admonition:: Debug Note

   The default admonition has no colors. It is gray.

.. attention:: Attention please!

.. caution:: Attention please!

.. danger:: This is a danger area.

.. error:: This is an error message.

.. hint:: This is hint message.

.. important:: This is an important message.

.. note::
   This page is showing markup styles, they have no meanings.

   Oh. Except this message.

.. tip:: A small tip please.

.. warning:: Please don't do anything harmful to me.


Sphinx Admonitions
~~~~~~~~~~~~~~~~~~

.. versionadded:: 2.5
   The *spam* parameter.

.. versionchanged:: 2.5
   The *spam* parameter.

.. deprecated:: 3.1
   Use :func:`spam` instead.

.. seealso::
   It is also available at https://typlog.com/
