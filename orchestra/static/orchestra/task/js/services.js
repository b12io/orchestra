var serviceModule =  angular.module('orchestra.task.services', []);

serviceModule.factory('orchestraService', function() {
    var googleUtils = new function() {
        this.folders = new function() {
            this.externalUrl = function(id) {
                return 'https://drive.google.com/open?id=' + id;
            }
            this.embedUrl = function(id) {
                return 'https://drive.google.com/embeddedfolderview?id=' + id
            }
            this.embedListUrl = function(id) {
                return this.embedUrl(id) + '#list'
            }
            this.embedGridUrl = function(id) {
                return this.embedUrl(id) + '#grid'
            }
        }
        this.files = new function() {
            this.editUrl = function(id) {
                return 'https://docs.google.com/document/d/' + id + '/edit'
            }
        }
    }

    var taskUtils = new function() {
        this.findPrerequisite = function(parent_step, desired_slug) {
            var stepsToTraverse = [parent_step];
            while (stepsToTraverse.length) {
                var currentStep = stepsToTraverse.pop()
                if (currentStep.prerequisites[desired_slug]) {
                    return currentStep.prerequisites[desired_slug]
                }
                for (step_slug in currentStep.prerequisites) {
                    stepsToTraverse.push(currentStep.prerequisites[step_slug])
                }
            }
        };

        this.updateVersion = function(taskAssignment) {
          if (taskAssignment === undefined ||
              taskAssignment.task.data.__version <= 1) {
            taskAssignment.task.data = {
              __version: 1
            }
          }
        }
    }

    var orchestraService = new function() {
        this.googleUtils = googleUtils;
        this.taskUtils = taskUtils;
    }
    return orchestraService;
});
