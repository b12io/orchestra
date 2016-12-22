var serviceModule = angular.module('orchestra.common');

serviceModule.factory('orchestraApi', function($http, $resource) {
  var projectManagementBase = '/orchestra/api/interface/project_management/';

  function getApiUrl(endpoint) {
    return projectManagementBase + endpoint + '/';
  }

  function endpoint (modelName, actionName) {
    var url = '/orchestra/api_new/' + modelName.toLowerCase() + '/:id/';
    if (actionName) {
      url += actionName + '/';
    }
    return url
  }

  // TODO(jrbotros): webpack, ES6ify, clean up
  return {
    Iteration: $resource(endpoint('iteration'), { id: '@id' }),
    Project: $resource(endpoint('project'), { id: '@id' }, {
      abort: { method: 'POST', url: endpoint('project', 'abort') },
      add_slack_user: { method: 'POST', url: endpoint('project', 'add_slack_user') },
      remove_slack_user: { method: 'POST', url: endpoint('project', 'remove_slack_user') },
      create_subsequent_tasks: { method: 'POST', url: endpoint('project', 'create_subsequent_tasks') },
    }),
    Task: $resource(endpoint('task'), { id: '@id' }, {
      assign: { method: 'POST', url: endpoint('task', 'assign') },
      submit: { method: 'POST', url: endpoint('task', 'submit') },
      reject: { method: 'POST', url: endpoint('task', 'reject') },
      skip: { method: 'POST', url: endpoint('task', 'skip') },
      revert: { method: 'POST', url: endpoint('task', 'revert') },
    }),
    TaskAssignment: $resource(endpoint('taskassignment'), { id: '@id' }, {
      reassign: { method: 'POST', url: endpoint('taskassignment', 'reassign') },
    }),
    TimeEntry: $resource(endpoint('timeentry'), { id: '@id' }),
    Worker: $resource(endpoint('worker'), { id: '@id' }, {
      stop_timer: { method: 'POST', url: endpoint('worker', 'stop_timer') },
      start_timer: { method: 'POST', url: endpoint('worker', 'start_timer') },
    }),
    WorkerCertification: $resource(endpoint('workercertification'), { id: '@id' }),

    allProjects: function(projectId) {
      return $http.get(getApiUrl('projects'));
    },

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
