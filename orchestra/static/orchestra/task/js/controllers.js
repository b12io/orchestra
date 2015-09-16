(function () {
  'use strict';

  angular
    .module('orchestra.task.controllers')
    .controller('TaskController', TaskController);

  TaskController.$inject = ['$location', '$scope', '$routeParams', '$http', '$sce',
                            '$compile', '$modal', '$timeout', 'orchestraService'];

  function TaskController($location, $scope, $routeParams, $http, $sce,
                          $compile, $modal, $timeout, orchestraService) {
    var vm = this;
    vm.taskId = $routeParams.taskId;
    vm.taskAssignment = {};
    vm.angularDirective = '';

    // We dynamically inject the team messages iframe after we retrieve
    // the data about the task assignment. teamMessagesDirective contains
    // the HTML snippet that we dynamically inject.
    vm.teamMessagesDirective = '';
    vm.activate = function() {
      $http.post('/orchestra/api/interface/task_assignment_information/',
                 {'task_id': vm.taskId}).
        success(function(data, status, headers, config) {
          vm.taskAssignment = data;
          vm.project = data.project;
          vm.is_reviewer = data.is_reviewer;
          vm.is_read_only = data.is_read_only;
          vm.work_times_seconds = data.work_times_seconds;

          var projectFolderId = vm.taskAssignment.project.project_data.project_folder_id;
          vm.projectFolderEmbedUrl = orchestraService.googleUtils.folders.embedListUrl(projectFolderId)
          vm.projectFolderExternalUrl = orchestraService.googleUtils.folders.externalUrl(projectFolderId)

          vm.saveError = false;
          vm.saving = false;
          if (!vm.is_read_only) {
            vm.setupAutoSave();
          }

          var directiveTag = (window.orchestra
            .angular_directives[data.workflow.slug]
            [data.step.slug]);

          var inject = []
          if (directiveTag) {
            // Hyphenate and lowercase camel-cased directive names according to
            // angular standards.
            directiveTag = directiveTag.replace(/[A-Z]/g, function(letter, pos) {
                return (pos ? '-' : '') + letter.toLowerCase();
            });

            var inject = [
              '<',
                directiveTag,
              ' task-assignment="vm.taskAssignment"></',
                directiveTag,
                '>'].join('');
          }
          vm.angularDirective = inject;

          vm.teamMessagesDirective = ('<website-iframe title="Team Messages" ' +
                                      'id="team-messages"' +
                                      'iframe-url="{{vm.taskAssignment.project.review_document_url}}"> '+
                                      '</website-iframe>');
        });
    };

    // TODO(jrbotros): Move all save functionality into its own module
    vm.setupAutoSave = function() {
      vm.autoSaveTimeout = 10000;

      $scope.$watch('vm.taskAssignment.task.data', function(newVal, oldVal) {
        // Ensure save fired at initialization
        // [http://stackoverflow.com/a/18915585]
        if (newVal != oldVal) {
          vm.scheduleAutoSave();
        }
      }, true);

      // Browser close or reload
      window.onbeforeunload = function() {
        if (vm.autoSaveTimer || vm.saveError) {
          return 'Your latest changes haven\'t been saved.'
        }
      }

      // Angular location change
      $scope.$on('$locationChangeStart', function(e) {
        if (vm.autoSaveTimer || vm.saveError) {
          if (!confirm('Your latest changes haven\'t been saved.\n\n' +
                      'Are you sure you want to leave this page?')) {
            e.preventDefault();
          }
        }
      });
    }

    vm.scheduleAutoSave = function() {
      if (!vm.autoSaveTimer && !vm.is_read_only) {
        vm.autoSaveTimer = $timeout(function() {
          vm.saveTask();
        }, vm.autoSaveTimeout)
      }
    }

    vm.cancelAutoSave = function() {
      $timeout.cancel(vm.autoSaveTimer);
      vm.autoSaveTimer = undefined;
    }

    vm.saveTask = function() {
      if (vm.is_read_only) {
        return;
      }
      vm.saving = true;
      vm.saveError = false;
      vm.cancelAutoSave();
      $http.post('/orchestra/api/interface/save_task_assignment/',
                 {'task_id': vm.taskId, 'task_data': vm.taskAssignment.task.data})
        .success(function(data, status, headers, config) {
          vm.lastSaved = Date.now();
          // Reset timeout counter on save success
          vm.autoSaveTimeout = 10000;
        })
        .error(function(data, status, headers, config) {
          vm.saveError = true;
        })
        .finally(function() {
          vm.saving = false;
          if (vm.saveError) {
            // Retry save with exp backoff
            vm.autoSaveTimeout *= 2;
            vm.scheduleAutoSave();
          }
        });
    };

    vm.confirmSubmission = function(command, totalSeconds) {
      vm.submitting = true;
      $http.post('/orchestra/api/interface/submit_task_assignment/',
                 {'task_id': vm.taskId, 'task_data': vm.taskAssignment.task.data,
                  'command_type': command, 'work_time_seconds': totalSeconds})
        .success(function(data, status, headers, config) {
          // Prevent additional confirmation dialog on leaving the page; data
          // will be saved by submission
          vm.cancelAutoSave();
          $location.path('/');
        })
        .error(function(data, status, headers, config) {
        })
        .finally(function() {
          vm.submitting = false;
        });
    };

    vm.submitTask = function(command) {
      var modalInstance = $modal.open({
        templateUrl: 'submit_task_modal.html',
        controller: 'SubmitModalInstanceCtrl',
        size: 'sm',
        windowClass: 'modal-confirm-submit',
        resolve: {
          command: function () {
            return command;
          },
          work_times_seconds: function() {
            return vm.work_times_seconds;
          }
        },
      });

      modalInstance.result.then(function(totalSeconds){
        vm.confirmSubmission(command, totalSeconds);
      });
    };

    vm.activate();
  }

})();


(function () {
  'use strict';

  angular
    .module('orchestra.task.controllers')
    .controller('SubmitModalInstanceCtrl', SubmitModalInstanceCtrl);

  SubmitModalInstanceCtrl.$inject = ['$scope', '$modalInstance', 'command', 'work_times_seconds']

  function SubmitModalInstanceCtrl($scope, $modalInstance, command, workTimesSeconds) {
    $scope.command = command;
    $scope.currentIterationHours = null;
    $scope.currentIterationMinutes = null;
    $scope.workTimesSeconds = workTimesSeconds;

    $scope.submit = function() {
      $modalInstance.close($scope.totalSeconds());
    }

    $scope.cancel = function() {
      $modalInstance.dismiss('cancel');
    }

    $scope.totalSeconds = function() {
      var hours = parseInt($scope.currentIterationHours);
      var minutes = parseInt($scope.currentIterationMinutes);
      if (isNaN(hours)) {
        throw 'Please provide hours (0 is acceptable)';
      }
      if (hours.toString() !== $scope.currentIterationHours) {
        throw 'Hours should be a whole number'
      }
      if (hours < 0) {
        throw 'Hours should be >=0'
      }
      if (isNaN(minutes)) {
        throw 'Please provide minutes (0 is acceptable)';
      }
      if (minutes.toString() !== $scope.currentIterationMinutes) {
        throw 'Minutes should be a whole number'
      }
      if (minutes > 59 || minutes < 0) {
        throw 'Minutes should be <60 and >=0'
      }

      return (hours * 3600) + (minutes * 60);
    }

    $scope.secondsError = function() {
      try {
        $scope.totalSeconds();
      } catch (error) {
        return error;
      }

      return null;
    }

    $scope.hoursMinutes = function(seconds) {
      var hours = (seconds - (seconds % 3600)) / 3600;
      var minutes = (seconds % 3600) / 60;
      return [hours, minutes];
    }

    $scope.totalPreviousSeconds = function() {
      var total = 0;
      angular.forEach($scope.workTimesSeconds, function(seconds) {
        total += seconds;
      });
      return total;
    }

    $scope.totalPreviousHoursMinutes = function() {
      return $scope.hoursMinutes($scope.totalPreviousSeconds());
    }

    $scope.totalHoursMinutes = function() {
      var allSeconds = $scope.totalPreviousSeconds();;
      try {
        allSeconds += $scope.totalSeconds();
      } catch (error) {
      }
      return $scope.hoursMinutes(allSeconds);
    }

    $scope.$watchGroup(['currentIterationHours',
                        'currentIterationMinutes'],
                       function(newTimes, oldTimes) {
      for (var i=0; i < newTimes.length; i++) {
        if (newTimes[i] != oldTimes[i]) {
          $scope.secondsErrorMessage = $scope.secondsError();
        }
      }
    });
  }
})();


(function () {
  'use strict';

  angular
    .module('orchestra.task.controllers')
    .controller('IframeController', IframeController);

  IframeController.$inject = ['$scope', '$sce', '$timeout', '$compile']

  function IframeController($scope, $sce, $timeout, $compile) {
    $scope.activate = function() {
      // The iframe is actually added only after everything is loaded.
      // This way the webpage does not stall for a couple of seconds until
      // all the iframe directives load.
      $timeout(function(){
        var iframe = document.createElement('iframe');
        iframe.setAttribute('name', '{{title}}');
        iframe.setAttribute('class', 'website-iframe');
        iframe.setAttribute('id', 'iframe-' + $scope.id);
        iframe.setAttribute('frameBorder', 0);
        var parent = document.getElementById('iframe-wrapper-' + $scope.id);
        parent.appendChild(iframe);
        $scope.iframe = iframe;

        // The iframe directive runs before the iframeUrl is $applied (in cases
        // where it is dynamically populated by a service, e.g. googleUtils),
        // so we watch for its update.
        $scope.$watch('iframeUrl', function(newVal, oldVal) {
          $scope.trustedIframeUrl = $sce.trustAsResourceUrl($scope.iframeUrl);
          $scope.iframe.setAttribute('ng-src','{{trustedIframeUrl}}');
          $compile($scope.iframe)($scope);
        }, true);
      });
    };

    $scope.activate();
  }
})();
