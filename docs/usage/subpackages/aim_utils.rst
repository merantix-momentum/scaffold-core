.. _aim_utils:

Aim Utils
=======

This package contains a patch that allows :code:`aim` to use :code:`fsspec` to read and write artifacts.
Use it by calling the :code:`register_fsspec_to_aim` function before using aim functionality:

.. code-block:: python

    # Add fsspec functionality to the aim artifact registry
    from scaffold.aim_utils import register_fsspec_to_aim
    register_fsspec_to_aim()

.. note::
    Make sure to install the relevant fsspec implementations for the storage you want to use, for example ``s3fs`` for AWS S3 or ``gcsfs`` for Google Cloud Storage.
