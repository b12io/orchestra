import template from './todo-list.html'

export default function todoList (orchestraApi) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      projectId: '='
    },
    controllerAs: 'todoList',
    bindToController: true,
    controller: function () {
      var todoList = this
      todoList.possibleTasks = []
      console.log(todoList.projectId)
      orchestraApi.projectInformation(todoList.projectId)
        .then((response) => {
          const humanSteps = new Set(response.data.steps.filter(step => step.is_human).map(step => step.slug))
          todoList.possibleTasks = Object.values(response.data.tasks).filter(task => task.status !== 'Complete' && humanSteps.has(task.step_slug))
        })
    }
  }
}
