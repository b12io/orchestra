import template from './task-select.html'

export default function taskSelect (orchestraTasks) {
  'ngAnnotate'
  return {
    template,
    scope: {
      task: '='
    },
    controllerAs: 'taskSelect',
    bindToController: true,
    controller: function () {
      var taskSelect = this

      taskSelect.orchestraTasks = orchestraTasks
    }
  }
}
