
Notifications in Flyte Workflows
=================================
Flyte workflows support configurable notifications to inform users about specific execution phases, such as success or failure. 
Notifications can be sent via email or Slack, and they are defined within the flyte_launcher.yaml configuration file.

Configuring Notifications
--------------------------
To add notifications to your workflow, use the notifications key under hydra.launcher in flyte_launcher.yaml. Each notification specifies:

* **Type**: The communication method, such as email or slack.
* **Phases**: Workflow execution phases that trigger the notification, such as SUCCEEDED or FAILED.
* **Recipients**: A list of recipients who will be notified.

Below is an example configuration for enabling notifications:
.. code-block:: yaml
    :caption: flyte_launcher.yaml
    :emphasize-lines: 8,9,10,11,12,13,14,15,16,17,18,19

    defaults:
      - /scaffold/flyte_launcher/FlyteWorkflowConfig@hydra.launcher.workflow

    hydra:
      mode: MULTIRUN # enables execution with flyte launcher, which not possible with a single run
      launcher:
        execution_environment: remote
        notifications:
          - type: email
            phases:
              - SUCCEEDED
              - FAILED
            recipients:
              - admin@example.com
          - type: slack
            phases:
              - FAILED
            recipients:
              - admin@slack.com # Slack channel email address
        workflow:
          default_image:
            base_image: <url>/flyte # Your flyte image
            base_image_version: latest
            target_image: <url>/<your workflow name>
            dockerfile_path: infrastructure/docker/Dockerfile.flyte
            docker_context: . # Relative to project root, i.e. where your "setup.py" is.
            flyte_image_name: default
          project: default
          domain: development

Example Use Case
--------------------------
1. Email Notification:
An email is sent to admin@example.com when the workflow succeeds or fails.
2. Slack Notification:
A Slack notification is sent to admin@slack.com when the workflow fails.

Notes on Notifications
--------------------------
* Notifications help monitor workflow execution and quickly respond to critical events.
* Ensure that the recipient email addresses and Slack configurations are valid and accessible to the relevant stakeholders.
* This feature integrates seamlessly with Flyte workflow execution phases for improved observability.

For more details on configuring Notifications on Flyte workflows, refer to `the official documentation <https://docs.flyte.org/en/latest/deployment/configuration/notifications.html>`_.