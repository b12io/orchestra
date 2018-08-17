import dataModalTemplate from 'orchestra/project-management/data-modal.html'
import slackModalTemplate from 'orchestra/project-management/slack-modal.html'

let d3 = require('d3')

export default function projectVis (
    $uibModal, $location, dataService, orchestraApi, crosshair, visUtils,
    tasksVis, assignmentsVis, iterationsVis, axis) {
  /**
   * Service to coordinate and visualize the project management view.
   */
  'ngAnnotate'
  return {
    setup: function (scope, parentSelector, projectId) {
      var vis = this
      scope.vis = vis

      var params = {
        'scaleHeight': 40,
        'barHeight': 30,
        'lanePadding': {
          'top': 30,
          'bottom': 25
        },
        'marginLeft': 200,
        'marginRight': 50,
        'scaleWidth': 1350
      }

      visUtils.setup(d3.select(parentSelector), params)
      crosshair.setup()

      // Allow partial access to necessary services
      vis.axis = axis
      vis.dataService = dataService
      vis.params = visUtils.params

      var axisWrapper = visUtils.parentContainer
        .append('div')
        .attr('class', 'axis-wrapper')

      axisWrapper.append('svg')
        .attr({
          'class': 'x axis',
          'width': visUtils.getSvgWidth(),
          'height': visUtils.params.scaleHeight
        })
        .style('margin-left', visUtils.params.marginLeft)

      axisWrapper.append('span')
        .attr('class', 'x label')

      scope.$on('orchestra:projectManagement:dataUpdate', vis.draw)
      dataService.ready.then(function () {
        if (projectId) {
          dataService.changeProject(projectId)
          visUtils.parentContainer.node().scrollLeft = 100
        }
      })
    },
    draw: function () {
      /**
       * Draws/updates the project management visualization.
       */
      axis.draw()
      tasksVis.draw()
      crosshair.draw()
      visUtils.parentContainer.style({
        'margin-left': visUtils.svgLeftMargin() + 'px'
      })
    },
    createSubsequentTasks: function () {
      /**
       * Handles the promise returned by orchestraApi.createSubsequentTasks
       * in the visualization.
       */
      orchestraApi.createSubsequentTasks(dataService.currentProject.id)
        .then(function () {
          dataService.updateData()
        }, function (response) {
          var errorMessage = 'Could not create subsequent tasks.'
          if (response.status === 400) {
            errorMessage = response.data.message
          }
          window.alert(errorMessage)
        })
    },
    showProjectData: function () {
      /**
       * Displays project-level data in a modal.
       */
      $uibModal.open({
        template: dataModalTemplate,
        controller: function ($scope) {
          $scope.data = dataService.data.project
          $scope.header = dataService.data.project.short_description
          $scope.admin_url = dataService.data.project.admin_url
        }
      })
    },
    showSlackActions: function () {
      /**
       * Displays options to add/remove Slack users to the project group in
       * a modal.
       */
      var modalInstance = $uibModal.open({
        template: slackModalTemplate,
        controller: function ($scope, $log) {
          $scope.editSlackMembership = function (action, username) {
            orchestraApi.editSlackMembership(action, dataService.currentProject.id, username)
              .then(function () {
                modalInstance.close()
              }, function (response) {
                var errorMessage = 'Could not ' + action + ' user.'
                if (response.status === 400) {
                  errorMessage = response.data.message
                }
                window.alert(errorMessage)
              })
          }

          $scope.unarchiveSlackChannel = function () {
            orchestraApi.unarchiveSlackChannel(dataService.currentProject.id)
            .then(function () {
              modalInstance.close()
            })
          }
        }
      })
    },
    endProject: function () {
      /**
       * Handles the promise returned by orchestraApi.endProject in the
       * visualization.
       */
      if (window.confirm('Are you sure you want to end this project? This cannot be undone.')) {
        orchestraApi.endProject(dataService.currentProject.id)
          .then(function () {
            $location.path('/')
          }, function (response) {
            var errorMessage = 'Could not end project.'
            if (response.status === 400) {
              errorMessage = response.data.message
            }
            window.alert(errorMessage)
          })
      }
    }
  }
}
