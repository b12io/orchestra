import template from './team-info-card.html'
import moment from 'moment-timezone'

export default function teamInfoCard (orchestraApi) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      projectId: '='
    },
    controllerAs: 'teamInfoCard',
    bindToController: true,
    controller: ($scope) => {
      const teamInfoCard = $scope.teamInfoCard
      orchestraApi.projectInformation(teamInfoCard.projectId)
        .then(response => {
          const {steps, tasks} = response.data
          const humanSteps = new Set(steps.filter(step => step.is_human).map(step => step.slug))
          teamInfoCard.assignments = []
          for (let stepSlug of humanSteps.values()) {
            const task = tasks[stepSlug]
            if (task) {
              teamInfoCard.assignments = teamInfoCard.assignments.concat(task.assignments.map(a => {
                return {
                  role: stepSlug,
                  worker: a.worker,
                  recordedTime: moment.duration(a.recorded_work_time).roundMinute().humanizeUnits()
                }
              }))
            }
          }
        })
    }
  }
}
