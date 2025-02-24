Installation
=================

You can install the latest stable version of Scaffold via pip. Scaffold splits its dependencies into extras, so that technology specific functionality is optional.

Without any extras:

.. code-block::

    pip install mxm-scaffold

Install all, or pick specific extras:

.. code-block::

    pip install mxm-scaffold[all]
    pip install mxm-scaffold[flyte,torch]
