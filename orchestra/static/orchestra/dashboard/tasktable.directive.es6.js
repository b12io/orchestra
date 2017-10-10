import template from './tasktable.html'

export default function tasktable () {
  'ngAnnotate'

  return {
    template,
    restrict: 'A',
    scope: {
      tasktable: '='
    },
    controllerAs: 'vm',
    bindToController: true,
    controller: function ($location, $timeout, orchestraTasks) {
      const vm = this
      vm.openTask = (task) => {
        $location.path(`task/${task.id}`)
      }

      // Surface service to interpolator
      vm.orchestraTasks = orchestraTasks
      vm.enableNewTaskButtons = vm.tasktable.newTasks && window.orchestra.enable_new_task_buttons

      vm.waiting = true
      orchestraTasks.data.finally(() => { vm.waiting = false })

      vm.newTask = function (taskType) {
        // To allow users to read the "no tasks left" message while debouncing
        // further clicks, we leave the message up for 15 seconds before removing
        // it and re-enabling the buttons
        vm.waiting = true
        if (!vm.noTaskTimer) {
          // Initialize task timer to dummy value to prevent subsequent API calls
          vm.noTaskTimer = 'temp'
          orchestraTasks.newTask(taskType)
            .then(function (response) {
              $location.path('task/' + response.data.id)
              vm.noTaskTimer = undefined
              vm.waiting = false
              return response
            }, function (response) {
              vm.newTaskError = true
              // Rate limit button-clicking
              vm.noTaskTimer = $timeout(function () {
                vm.noTaskTimer = undefined
                vm.newTaskError = false
              }, 15000)
            })
        }
      }
    }
  }
}
