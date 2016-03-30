var serviceModule = angular.module('orchestra.common.services');

serviceModule.factory('orchestraApi', function($http) {
  var api = function() {
    var api = this;

    var projectManagementBase = '/orchestra/api/interface/project_management/';

    function apiUrl(endpoint) {
      return projectManagementBase + endpoint + '/';
    }

    api.projectInformation = function(projectId) {
      return $http.post(apiUrl('project_information'), {
        'project_id': projectId
      });
    };

    api.completeAndSkipTask = function(task) {
      return $http.post(apiUrl('complete_and_skip_task'), {
        'task_id': task.id
      });
    };

    api.assignTask = function(task, workerUsername) {
      return $http.post(apiUrl('assign_task'), {
        'worker_username': workerUsername,
        'task_id': task.id
      });
    };

    api.reassignAssignment = function(assignment, workerUsername) {
      return $http.post(apiUrl('reassign_assignment'), {
        'worker_username': workerUsername,
        'assignment_id': assignment.id
      });
    };

    api.revertTask = function(taskId, datetime, fake) {
      return $http.post(apiUrl('revert_task'), {
        'task_id': taskId,
        // Provide seconds rather than milliseconds to the API
        'revert_datetime': datetime.getTime() / 1000,
        'fake': fake || false
      });
    };

    api.createSubsequentTasks = function(projectId) {
      return $http.post(apiUrl('create_subsequent_tasks'), {
        'project_id': projectId,
      });
    };

    api.editSlackMembership = function(action, projectId, username) {
      return $http.post(apiUrl('edit_slack_membership'), {
        'action': action,
        'project_id': projectId,
        'username': username
      });
    };

    api.endProject = function(projectId) {
      return $http.post(apiUrl('end_project'), {
        'project_id': projectId,
      });
    };
  };
  return api;
});
