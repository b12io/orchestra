API Reference
=============

.. _client_api:

Client API
----------
Endpoints for communicating with Orchestra.

All requests must be signed using `HTTP signatures <http://tools.ietf.org/html/draft-cavage-http-signatures-03>`_:

.. sourcecode:: python

   from httpsig.requests_auth import HTTPSignatureAuth

   auth = HTTPSignatureAuth(key_id=settings.ORCHESTRA_PROJECT_API_KEY,
                            secret=settings.ORCHESTRA_PROJECT_API_SECRET,
                            algorithm='hmac-sha256')
   response = requests.get('https://www.example.com/orchestra/api/project/create_project', auth=auth)


.. http:post:: /orchestra/api/project/create_project

   Creates a project with the given data and returns its ID.

   :query task_class: One of `real` or `training` to specify the task class type.
   :query workflow_slug: The slug corresponding to the desired project's workflow.
   :query workflow_version_slug: The slug corresponding to the desired version of the workflow.
   :query description: A short description of the project.
   :query priority: An integer describing the priority of the project, with higher numbers describing a greater priority.
   :query project_data: Other miscellaneous data with which to initialize the project.

   **Example response**:

   .. sourcecode:: json

      {
        "project_id": 123,
      }


.. http:post:: /orchestra/api/project/project_information

   Retrieve detailed information about a given project.

   :query project_id: The ID for the desired project.

   **Example response**:

   .. sourcecode:: json

      {
          "project": {
              "id": 123,
              "short_description": "Project Description",
              "priority": 10,
              "team_messages_url": "http://review.document.url",
              "task_class": 1,
              "project_data": {
                  "sample_data_item": "sample_data_value_new"
              },
              "workflow_slug": "sample_workflow_slug",
              "workflow_version_slug": "v1",
              "start_datetime": "2015-09-23T20:16:02.667288Z"
          },
          "steps": [
              ["sample_step_slug", "Sample step description"]
          ],
          "tasks": {
              "sample_step_slug": {
                  "id": 456,
                  "project": 123,
                  "status": "Processing",
                  "step_slug": "sample_step_slug",
                  "latest_data": {
                    "sample_data_item": "sample_data_value_new"
                  },
                  "assignments": [
                      {
                          "id": 558,
                          "snapshots": {
                              "__version": 1,
                              "snapshots": [
                                  {
                                      "work_time_seconds": 3660,
                                      "datetime": "2015-09-23T20:16:15.821171",
                                      "data": {
                                          "sample_data_item": "sample_data_value_old",
                                          "__version": 1
                                      },
                                      "type": 0
                                  }
                              ]
                          },
                          "worker": "sample_worker_username",
                          "task": 456,
                          "in_progress_task_data": {
                              "sample_data_item": "sample_data_value_new"
                          },
                          "status": "Processing",
                          "start_datetime": "2015-09-23T20:16:17.355291Z"
                      }
                  ]
              }
          }
      }

.. http:get:: /orchestra/api/project/workflow_types

   Return all stored workflows and their versions.

   **Example response**:

   .. sourcecode:: json

      {
          "workflows": {
	      "journalism": {
	          "name": "Journalism Workflow",
		  "versions": {
		      "v1": {
		          "name": "Journalism Workflow Version 1",
			  "description": "Create polished newspaper articles from scratch."
		      },
		      "v2": {
		          "name": "Journalism Workflow Version 2",
			  "description": "Create polished newspaper articles from scratch."
		      }
                  }
	      },
	      "simple_workflow": {
	          "name": "Simple Workflow",
		  "versions": {
		      "v1": {
		          "name": "Simple Workflow Version 1",
			  "description": "Crawl a web page for an image and rate it."
		      }
		  }
	      }
	  }
      }
