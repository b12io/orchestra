import { reduce } from 'lodash'
import template from './team-info-card.html'
import moment from 'moment-timezone'

export default function teamInfoCard (orchestraApi) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      taskAssignment: '='
    },
    controllerAs: 'teamInfoCard',
    bindToController: true,
    controller: ($scope) => {
      const teamInfoCard = $scope.teamInfoCard
      teamInfoCard.projectId = teamInfoCard.taskAssignment.project.id
      teamInfoCard.projectStatus = teamInfoCard.taskAssignment.project.status
      teamInfoCard.step = teamInfoCard.taskAssignment.step
      teamInfoCard.isProjectAdmin = teamInfoCard.taskAssignment.is_project_admin
      teamInfoCard.sentStaffBotRequest = {}

      teamInfoCard.loadTeamInfo = () => {
        orchestraApi.projectInformation(teamInfoCard.projectId)
          .then(response => {
            const data = response.data[teamInfoCard.projectId]
            const {steps, tasks} = data
            const humanSteps = new Set(steps.filter(step => step.is_human).map(step => step.slug))
            teamInfoCard.steps = reduce(
              Object.values(steps), (result, step) => {
                result[step.slug] = step
                return result
              }, {})
            teamInfoCard.assignments = []
            for (let stepSlug of humanSteps.values()) {
              const task = tasks[stepSlug]
              if (task) {
                teamInfoCard.assignments = teamInfoCard.assignments.concat(task.assignments.map(a => {
                  const workTime = moment.duration(a.recorded_work_time, 'seconds')
                  const workDayDisplay = workTime.days() > 0 ? `${workTime.days()}d ` : ''
                  const workTimeString = `${workDayDisplay}${workTime.hours()}h ${workTime.minutes()}m`
                  return {
                    stepSlug,
                    role: teamInfoCard.steps[stepSlug].name,
                    worker: a.worker,
                    recordedTime: workTimeString,
                    task_status: task.status,
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

      teamInfoCard.restaff = (taskId, stepSlug) => {
        teamInfoCard.sentStaffBotRequest[stepSlug] = 'Sending request...'
        orchestraApi.staffTask(taskId).then(() => {
          teamInfoCard.sentStaffBotRequest[stepSlug] = 'StaffBot request sent'
        }, () => {
          var errorMessage = 'Error creating a StaffBot request.'
          window.alert(errorMessage)
          delete teamInfoCard.sentStaffBotRequest[stepSlug]
        })
      }

      teamInfoCard.togglePauseProject = () => {
        const newStatus = (teamInfoCard.projectStatus === 'Paused'
          ? 'Active' : 'Paused')

        orchestraApi.setProjectStatus(teamInfoCard.projectId, newStatus)
          .then(({data}) => {
            if (data.success) {
              const changedStatus = data.status === 'Paused' ? 'paused' : 'reactivated'
              window.alert(`The project has been ${changedStatus}.`)
              teamInfoCard.projectStatus = data.status
            }
          })
      }

      teamInfoCard.loadTeamInfo()
    }
  }
}
