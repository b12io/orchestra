export default function orchestraApi ($http) {
  var projectManagementBase = '/orchestra/api/interface/project_management/'

  function getApiUrl (endpoint) {
    return projectManagementBase + endpoint + '/'
  }

  return {
    allProjects: function (projectId) {
      return $http.get(getApiUrl('projects'))
    },

    projectInformation: function (projectId) {
      return $http.post(getApiUrl('project_information'), {
        'project_id': projectId
      })
    },

    completeAndSkipTask: function (taskId) {
      return $http.post(getApiUrl('complete_and_skip_task'), {
        'task_id': taskId
      })
    },

    assignTask: function (taskId, workerUsername) {
      return $http.post(getApiUrl('assign_task'), {
        'worker_username': workerUsername,
        'task_id': taskId
      })
    },

    reassignAssignment: function (assignmentId, workerUsername) {
      return $http.post(getApiUrl('reassign_assignment'), {
        'worker_username': workerUsername,
        'assignment_id': assignmentId
      })
    },

    staffTask: function (taskId) {
      return $http.post(getApiUrl('staff_task'), {
        'task_id': taskId
      })
    },

    revertTask: function (taskId, iterationId, revertBefore, commit) {
      return $http.post(getApiUrl('revert_task'), {
        'task_id': taskId,
        'iteration_id': iterationId,
        'revert_before': revertBefore || false,
        'commit': commit || false
      })
    },

    createSubsequentTasks: function (projectId) {
      return $http.post(getApiUrl('create_subsequent_tasks'), {
        'project_id': projectId
      })
    },

    editSlackMembership: function (action, projectId, username) {
      return $http.post(getApiUrl('edit_slack_membership'), {
        'action': action,
        'project_id': projectId,
        'username': username
      })
    },

    unarchiveSlackChannel: function (projectId) {
      return $http.post(getApiUrl('unarchive_slack_channel'), {
        'project_id': projectId
      })
    },

    setProjectStatus: function (projectId, status) {
      return $http.post(getApiUrl('set_project_status'), {
        'project_id': projectId,
        'status': status
      })
    },

    endProject: function (projectId) {
      return $http.post(getApiUrl('end_project'), {
        'project_id': projectId
      })
    }
  }
};
