import { reduce } from 'lodash'
import template from './team-info-card.html'
import moment from 'moment-timezone'

export default function teamInfoCard (orchestraApi, helpers) {
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
      teamInfoCard.showUnassigned = false
      teamInfoCard.assignmentInput = {}
      teamInfoCard.loading = false

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
            teamInfoCard.unassigned = []
            for (let stepSlug of humanSteps.values()) {
              const task = tasks[stepSlug]
              if (task) {
                teamInfoCard.assignments = teamInfoCard.assignments.concat(task.assignments.map(a => {
                  const workTime = moment.duration(a.recorded_work_time, 'seconds')
                  const workDayDisplay = workTime.days() > 0 ? `${workTime.days()}d ` : ''
                  const workTimeString = `${workDayDisplay}${workTime.hours()}h ${workTime.minutes()}m`
                  teamInfoCard.assignmentInput[stepSlug] = a.worker.username
                  return {
                    stepSlug,
                    role: teamInfoCard.steps[stepSlug].name,
                    worker: a.worker,
                    recordedTime: workTimeString,
                    task_status: task.status,
                    id: a.id,
                    task_id: a.task
                  }
                }))
                if (task.assignments.length === 0) {
                  teamInfoCard.assignmentInput[stepSlug] = ''
                  teamInfoCard.unassigned.push({
                    stepSlug,
                    role: teamInfoCard.steps[stepSlug].name,
                    worker: null,
                    recordedTime: '0h 0m',
                    task_status: task.status,
                    task_id: task.id
                  })
                }
              }
            }
            const sortedStepSlugs = helpers.getSortedTasksSlugs(tasks)
            helpers.orderAssigmentsUsingListOfSlugs(sortedStepSlugs, teamInfoCard.unassigned)
            helpers.orderAssigmentsUsingListOfSlugs(sortedStepSlugs, teamInfoCard.assignments)
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

      teamInfoCard.staff = (taskId, stepSlug) => {
        teamInfoCard.sentStaffBotRequest[stepSlug] = 'Sending request...'
        orchestraApi.staffTask(taskId).then(() => {
          teamInfoCard.sentStaffBotRequest[stepSlug] = 'StaffBot request sent'
        }, () => {
          var errorMessage = 'Error creating a StaffBot request.'
          window.alert(errorMessage)
          delete teamInfoCard.sentStaffBotRequest[stepSlug]
        })
      }

      teamInfoCard.handleAssignmentKeydown = (taskId, assignmentId, stepSlug, worker) => {
        if (!worker) {
          teamInfoCard.assignTask(taskId, stepSlug)
        } else {
          teamInfoCard.reassignAssignment(assignmentId, stepSlug)
        }
      }

      teamInfoCard.assignTask = (taskId, stepSlug) => {
        teamInfoCard.loading = true
        orchestraApi.assignTask(taskId, teamInfoCard.assignmentInput[stepSlug])
          .then(function () {
            delete teamInfoCard.assignmentInput[stepSlug]
            teamInfoCard.loadTeamInfo()
          }, function (response) {
            teamInfoCard.assignmentInput[stepSlug] = ''
            var errorMessage = 'Error assigning task.'
            if (response.status === 400) {
              errorMessage = response.data.message
            }
            window.alert(errorMessage)
          })
          .finally(function () {
            teamInfoCard.loading = false
          })
      }

      teamInfoCard.reassignAssignment = (assignmentId, stepSlug) => {
        teamInfoCard.loading = true
        orchestraApi.reassignAssignment(assignmentId, teamInfoCard.assignmentInput[stepSlug])
          .then(function () {
            delete teamInfoCard.assignmentInput[stepSlug]
          }, function (response) {
            var errorMessage = 'Error reassigning worker.'
            if (response.status === 400) {
              errorMessage = response.data.message
            }
            window.alert(errorMessage)
          })
          .finally(function () {
            teamInfoCard.loadTeamInfo()
            teamInfoCard.loading = false
          })
      }

      teamInfoCard.toggleShowUnassigned = () => {
        teamInfoCard.showUnassigned = !teamInfoCard.showUnassigned
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

      teamInfoCard.isTaskStaffable = (status) => {
        return helpers.isTaskStaffable(status)
      }

      teamInfoCard.isStaffBotRequestBtnDisabled = (stepSlug) => {
        return teamInfoCard.sentStaffBotRequest[stepSlug] && teamInfoCard.sentStaffBotRequest[stepSlug].length > 0
      }

      teamInfoCard.loadTeamInfo()
    }
  }
}
