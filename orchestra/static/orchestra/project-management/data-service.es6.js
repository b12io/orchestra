export default function dataService ($location, $rootScope, $route, orchestraApi, helpers) {
  /**
   * Service to share and manipulate project management data across
   * visualization components.
   */
  'ngAnnotate'
  var _meta
  var _now = new Date()

  var service = {
    currentProject: {short_description: 'Select project to display', id: null, status: null},
    dataReady: null,
    allProjects: {},
    resetData: function (projectId) {
      _meta = {
        'tasks': {}
      }
    },
    getAllProjects: function () {
      var dataService = this
      dataService.loading = true
      dataService.ready = orchestraApi.allProjects().then(function (response) {
        response.data.forEach(function (project) {
          dataService.allProjects[project.id] = project
        })
        dataService.loading = false
      })
      return dataService.ready
    },
    setSelectedProject: function () {
      $route.updateParams({projectId: this.currentProject.id})
      this.resetData()
      return this.updateData()
    },
    setCurrentProjectStatus: function (status) {
      orchestraApi.setProjectStatus(this.currentProject.id, status)
        .then(({data}) => {
          if (data.success) {
            const changedStatus = data.status === 'Paused' ? 'paused' : 'reactivated'
            window.alert(`The project has been ${changedStatus}.`)
            this.currentProject.status = data.status
          }
        })
    },
    changeProject: function (projectId) {
      this.ready.then(function () {
        if (!projectId || !this.allProjects[projectId]) {
          $route.updateParams({projectId: undefined})
          return
        }

        this.currentProject = this.allProjects[projectId]
        return this.setSelectedProject()
      }.bind(this))
    },
    updateData: function () {
      /**
       * Retrieves latest project data from Orchestra.
       */
      var dataService = this
      dataService.loading = true
      dataService.ready = orchestraApi.projectInformation(this.currentProject.id)
        .then(function (response) {
          dataService.setData(response.data)
          if (dataService.data[dataService.currentProject.id].project.status === 'Aborted') {
            window.alert('Project is aborted.')
            $location.path('/')
          } else {
            $rootScope.$broadcast('orchestra:projectManagement:dataUpdate')
          }
          dataService.loading = false
        }, function (response) {
          var errorMessage = 'Error updating data.'
          if (response.status === 400) {
            errorMessage = response.data.message
          }
          window.alert(errorMessage)
        })
      return dataService.ready
    },
    setData: function (data) {
      /**
       * Prepares raw project data for visualization.
       */
      this.data = data

      var steps = {}
      this.data[this.currentProject.id].steps.forEach(function (step) {
        steps[step.slug] = step
      })

      this.data[this.currentProject.id].steps = steps

      /* jshint -W083 */
      // Hide error for creating a function in a loop
      for (var stepSlug in this.data[this.currentProject.id].tasks) {
        var task = this.data[this.currentProject.id].tasks[stepSlug]
        task.is_human = this.data[this.currentProject.id].steps[task.step_slug].is_human
        if (this.awaitingAssignment(task)) {
          // TODO(jrbotros): create the empty assignment in a saner way
          task.assignments.push({
            iterations: [],
            start_datetime: task.start_datetime,
            status: 'Processing',
            worker: {id: null, username: null}
          })
        }
        task.assignments.forEach(function (assignment) {
          assignment.task = task
          assignment.iterations.forEach(function (iteration, i) {
            iteration.assignment = assignment
          })
        })
      }

      var dataService = this
      this.timeSortedSlugs = helpers.getSortedTasksSlugs(this.data[dataService.currentProject.id].tasks)
    },
    taskFromKey: function (key) {
      /**
       * Returns the task for a given key.
       */
      return this.data[this.currentProject.id].tasks[key]
    },
    keyFromTask: function (task) {
      /**
       * Returns the key for a given task.
       */
      return task.step_slug
    },
    awaitingAssignment: function (task) {
      /**
       * Determines whether task can be given a new assignment.
       */
      var statuses = ['Awaiting Processing', 'Pending Review']
      return statuses.indexOf(task.status) >= 0
    },
    inProgressAssignment: function (task) {
      /**
       * Determines whether task has a currently-processing assignment.
       */
      var statuses = ['Processing', 'Post-review Processing', 'Reviewing']
      return statuses.indexOf(task.status) >= 0 || this.awaitingAssignment(task)
    },
    taskMeta: function (taskKey, metaKey, value) {
      /**
       * Stores and reads keyed task metadata. Since we update data from the
       * server, we store task visualization data separately so it's not
       * overwritten.
       */
      var taskMeta = _meta.tasks[taskKey] || {}
      if (value !== undefined) {
        taskMeta[metaKey] = value
        _meta.tasks[taskKey] = taskMeta
      } else {
        return taskMeta[metaKey]
      }
    },
    taskEnd: function (task) {
      /**
       * Calculates the end time for a given task.
       */
      if (this.awaitingAssignment(task)) {
        return _now.toString()
      }
      var taskEnd = task.start_datetime
      task.assignments.forEach(function (assignment) {
        if (assignment.iterations.length) {
          var lastIteration = assignment.iterations[assignment.iterations.length - 1]
          if (new Date(lastIteration.end_datetime) > new Date(taskEnd)) {
            taskEnd = lastIteration.end_datetime
          }
        }
      })
      return taskEnd
    },

    assignmentFromKey: function (key) {
      /**
       * Returns the assignment for a given key.
       */
      return this.taskFromKey(key.taskKey)
        .assignments[key.assignmentIndex]
    },
    keyFromAssignment: function (assignment) {
      /**
       * Returns the key for a given assignment.
       */
      var dataService = this
      return {
        'taskKey': dataService.keyFromTask(assignment.task),
        'assignmentIndex': dataService.indexFromAssignment(assignment)
      }
    },
    indexFromAssignment: function (assignment) {
      /**
       * Returns the assignment counter for a given assignment.
       */
      return assignment.task.assignments.indexOf(assignment)
    },

    iterationFromKey: function (key) {
      /**
       * Returns the iteration for the given key.
       */
      return this.assignmentFromKey(key.assignmentKey).iterations[key.iterationIndex]
    },
    keyFromIteration: function (iteration) {
      /**
       * Returns the key for a given iteration.
       */
      var dataService = this
      return {
        'assignmentKey': dataService.keyFromAssignment(iteration.assignment),
        'iterationIndex': iteration.assignment.iterations.indexOf(iteration)
      }
    }
  }

  service.getAllProjects()
  return service
}
