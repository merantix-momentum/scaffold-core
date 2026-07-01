.. _secrets-plugins:

Secrets Plugins
================

Scaffold provides Hydra plugins for seamless integration with cloud secret managers. These plugins register custom OmegaConf resolvers that fetch secrets on-demand during configuration resolution, allowing secure injection of secrets into your configs without hardcoding values.

**Supported Providers:**

* AWS Secrets Manager (``aws_secrets`` extra)
* Google Cloud Secret Manager (``gcp_secrets`` extra)
* Azure Key Vault (``azure_secrets`` extra)

Features
--------

* **Lazy Evaluation:** Secrets are fetched only when accessed, not at config load time
* **Automatic Registration:** Plugins auto-register on Hydra initialization via plugin discovery
* **JSON Support:** Extract specific keys from JSON-formatted secrets
* **No Hardcoded Values:** Config files show only resolver strings, never actual secrets
* **Type Safe:** Proper error messages for misconfiguration

Installation
------------

Install the cloud provider extra you need:

.. code-block:: bash

    # AWS
    pip install mxm-scaffold[aws_secrets]

    # Google Cloud
    pip install mxm-scaffold[gcp_secrets]

    # Azure
    pip install mxm-scaffold[azure_secrets]

Or install all secrets plugins:

.. code-block:: bash

    pip install mxm-scaffold[all]

Google Cloud Secret Manager (GCP)
----------------------------------

The GCP plugin provides a ``gcp_secret`` resolver for accessing secrets from GCP Secret Manager.

Configuration in YAML
""""""""""""""""""""""

.. code-block:: yaml

    database:
      # Simple string secret
      password: "${gcp_secret:my-project-id/db-password}"

      # Extract a key from a JSON secret
      username: "${gcp_secret:my-project-id/db-credentials,username}"
      api_key: "${gcp_secret:my-project-id/db-credentials,api_key}"

    auth:
      # Using full resource name
      token: "${gcp_secret:projects/my-project-123/secrets/auth-token/versions/latest}"

Authentication
"""""""""""""""

GCP Secret Manager uses Application Default Credentials. Ensure your environment is configured:

.. code-block:: bash

    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

Testing with Real GCP Resources
"""""""""""""""""""""""""""""""""

To test the GCP plugin with actual secrets:

1. **Install dependencies:**

   .. code-block:: bash

       uv sync --extra gcp_secrets

2. **Update the test configuration** at ``test/hydra_plugins/manual/gcp_secret_real_case.yaml``:

   Replace ``my-project-id`` and secret names with your actual GCP project ID and secret names:

   .. code-block:: yaml

       secrets:
         service_token: "${gcp_secret:YOUR-GCP-PROJECT-ID/your-secret-name}"
         db_username: "${gcp_secret:YOUR-GCP-PROJECT-ID/db-credentials,username}"
         db_password: "${gcp_secret:YOUR-GCP-PROJECT-ID/db-credentials,password}"

3. **Set up GCP credentials:**

   .. code-block:: bash

       export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

4. **Run the integration test:**

   .. code-block:: bash

       python test/hydra_plugins/manual/run_gcp_secret_real_case.py

   This will resolve all ``gcp_secret`` interpolations against real GCP Secret Manager. By default, secret values are redacted for safety. To see full values (on secure terminals only):

   .. code-block:: bash

       python test/hydra_plugins/manual/run_gcp_secret_real_case.py --show-values

AWS Secrets Manager
--------------------

The AWS plugin provides an ``aws_secret`` resolver for accessing secrets from AWS Secrets Manager.

Configuration in YAML
""""""""""""""""""""""

.. code-block:: yaml

    database:
      password: "${aws_secret:my-database-secret}"
      username: "${aws_secret:my-database-secret,username}"

See ``src/hydra_plugins/aws_secrets_plugin/README.md`` for detailed documentation.

Azure Key Vault
----------------

The Azure plugin provides an ``azure_secret`` resolver for accessing secrets from Azure Key Vault.

Configuration in YAML
""""""""""""""""""""""

.. code-block:: yaml

    database:
      password: "${azure_secret:my-vault,my-secret}"

See ``src/hydra_plugins/azure_secrets_plugin/README.md`` for detailed documentation.
