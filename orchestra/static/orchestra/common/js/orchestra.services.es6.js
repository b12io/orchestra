export function orchestraService () {
  'ngAnnotate'
  var googleUtils = {
    folders: {
      externalUrl: function (id) {
        return 'https://drive.google.com/open?id=' + id
      },
      embedUrl: function (id) {
        return 'https://drive.google.com/embeddedfolderview?id=' + id
      },
      embedListUrl: function (id) {
        return this.embedUrl(id) + '#list'
      },
      embedGridUrl: function (id) {
        return this.embedUrl(id) + '#grid'
      }
    },
    files: {
      editUrl: function (id) {
        return 'https://docs.google.com/document/d/' + id + '/edit'
      }
    }
  }
  var taskUtils = {
    prerequisiteData: function (taskAssignment, desiredStep, dataKey) {
      var previousData = taskAssignment.prerequisites[desiredStep]
      if (dataKey && previousData) {
        return previousData[dataKey]
      }
      return previousData
    },
    updateVersion: function (taskAssignment) {
      if (taskAssignment === undefined ||
        taskAssignment.task.data.__version <= 1) {
        taskAssignment.task.data = {
          __version: 1
        }
      }
    }
  }
  var registered = {}
  var signals = {
    registerSignal: function (signalType, callback) {
      registered[signalType] = registered[signalType] || []
      registered[signalType].push(callback)
    },
    fireSignal: function (signalType) {
      registered[signalType] = registered[signalType] || []
      const callbacks = registered[signalType]
      // Callbacks can be both functions and promises
      const calledOnes = callbacks.map(callback => callback())
      return Promise.all(calledOnes)
        .then(values => {
          const isFailure = new Set(values).has(false)
          return !isFailure
        })
    }
  }

  var orchestraService = {
    googleUtils: googleUtils,
    taskUtils: taskUtils,
    signals: signals
  }
  return orchestraService
}

export function orchestraTasks ($http) {
  'ngAnnotate'
  const activeState = (task) => ['just_added', 'in_progress', 'returned'].indexOf(task.state) !== -1
  const pendingState = (task) => ['pending_review', 'pending_processing'].indexOf(task.state) !== -1
  const activeTask = (task) => activeState(task) && task.should_be_active
  const pendingTask = (task) => (activeState(task) && !task.should_be_active) || pendingState(task)
  const pausedTask = (task) => task.state === 'paused'

  var orchestraTasks = {
    data: null,
    tasks: [],
    tasksByAssignmentId: {},
    preventNew: false,
    reviewerStatus: false,
    currentTask: undefined,
    updateTasks: function () {
      var service = this

      service.data = $http.get('/orchestra/api/interface/dashboard_tasks/')
        .then(function (response) {
          service.tasks = response.data.tasks

          service.allTasks().forEach(function (task) {
            service.tasksByAssignmentId[task.assignment_id] = task
          })

          service.preventNew = response.data.preventNew
          service.reviewerStatus = response.data.reviewerStatus
        })
    },
    newTask: function (taskType) {
      var service = this

      return $http.get('/orchestra/api/interface/new_task_assignment/' + taskType + '/')
        .then(function (response) {
          var task = response.data
          task.state = 'just_added'
          service.tasks.push(task)
          service.tasksByAssignmentId[task.assignment_id] = task
          return response
        })
    },
    allTasks: function () { return this.tasks },
    activeTasks: function () { return this.allTasks().filter(task => activeTask(task)) },
    pendingTasks: function () { return this.allTasks().filter(task => pendingTask(task)) },
    pausedTasks: function () { return this.allTasks().filter(task => pausedTask(task)) },
    completedTasks: function () { return this.allTasks().filter(task => task.state === 'complete') },
    activePendingAndRecentTasks: function (numRecent) {
      // Return all active tasks, pending tasks, as well as `numRecent` of the most
      // recently completed tasks.
      var tasks = this.activeTasks().concat(this.pendingTasks())
      return tasks.concat(this.completedTasks().slice(0, numRecent))
    },
    getDescription: function (task) {
      if (task) {
        return task.detail + ' (' + task.step + ')'
      }
    }
  }

  orchestraTasks.updateTasks()
  return orchestraTasks
}
