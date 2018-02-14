import { reduce } from 'lodash'
import template from './team-info-card.html'
import moment from 'moment-timezone'

export default function teamInfoCard (orchestraApi) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      taskAssignment: '=',
    },
    controllerAs: 'teamInfoCard',
    bindToController: true,
    controller: ($scope) => {
      const teamInfoCard = $scope.teamInfoCard
      teamInfoCard.projectId = teamInfoCard.taskAssignment.project.id
      teamInfoCard.step = teamInfoCard.taskAssignment.step
      teamInfoCard.isProjectAdmin = teamInfoCard.taskAssignment.is_project_admin

      teamInfoCard.loadTeamInfo = () => {
        orchestraApi.projectInformation(teamInfoCard.projectId)
          .then(response => {
            const {steps, tasks} = response.data
            const humanSteps = new Set(steps.filter(step => step.is_human).map(step => step.slug))
            teamInfoCard.steps = reduce(
              Object.values(response.data.steps), (result, step) => {
                result[step.slug] = step
                return result
              }, {})
            teamInfoCard.assignments = []
            for (let stepSlug of humanSteps.values()) {
              const task = tasks[stepSlug]
              if (task) {
                teamInfoCard.assignments = teamInfoCard.assignments.concat(task.assignments.map(a => {
                  return {
                    stepSlug,
                    role: teamInfoCard.steps[stepSlug].name,
                    worker: a.worker,
                    recordedTime: moment.duration(a.recorded_work_time, 'seconds').roundMinute().humanizeUnits(),
                    status: task.status,
                    task_id: a.task
                  }
                }))
              }
            }
          })
      }
      teamInfoCard.submitTask = (taskId) => {
        orchestraApi.completeAndSkipTask(taskId)
          .then(() => {
            teamInfoCard.loadTeamInfo()
          }, (response) => {
            let errorMessage = 'Error completing task.'
            if (response.status === 400) {
              errorMessage = response.data.message
            }
            window.alert(errorMessage)
          })
      }

      teamInfoCard.loadTeamInfo()
    }
  }
}
