var serviceModule = angular.module('orchestra.common');

serviceModule.factory('orchestraApi', function($http) {
  var projectManagementBase = '/orchestra/api/interface/project_management/';

  function getApiUrl(endpoint) {
    return projectManagementBase + endpoint + '/';
  }

  return {

    projectInformation: function(projectId) {
      return $http.post(getApiUrl('project_information'), {
        'project_id': projectId
      });
    },

    completeAndSkipTask: function(task) {
      return $http.post(getApiUrl('complete_and_skip_task'), {
        'task_id': task.id
      });
    },

    assignTask: function(task, workerUsername) {
      return $http.post(getApiUrl('assign_task'), {
        'worker_username': workerUsername,
        'task_id': task.id
      });
    },

    reassignAssignment: function(assignment, workerUsername) {
      return $http.post(getApiUrl('reassign_assignment'), {
        'worker_username': workerUsername,
        'assignment_id': assignment.id
      });
    },

    revertTask: function(taskId, iterationId, revertBefore, commit) {
      return $http.post(getApiUrl('revert_task'), {
        'task_id': taskId,
        'iteration_id': iterationId,
        'revert_before': revertBefore || false,
        'commit': commit || false
      });
    },

    createSubsequentTasks: function(projectId) {
      return $http.post(getApiUrl('create_subsequent_tasks'), {
        'project_id': projectId,
      });
    },

    editSlackMembership: function(action, projectId, username) {
      return $http.post(getApiUrl('edit_slack_membership'), {
        'action': action,
        'project_id': projectId,
        'username': username
      });
    },

    endProject: function(projectId) {
      return $http.post(getApiUrl('end_project'), {
        'project_id': projectId,
      });
    },
  };
});
