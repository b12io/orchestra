(function() {
  'use strict';

  angular.module('orchestra.timing')
    .directive('taskSelect', function(orchestraTasks) {
      return {
        scope: {
          task: '=',
        },
        templateUrl: $static('/static/orchestra/timing/timecard/partials/task-select.html'),
        controllerAs: 'taskSelect',
        bindToController: true,
        controller: function() {
          var taskSelect = this;

          taskSelect.orchestraTasks = orchestraTasks;
        }
      };
    })
    .directive('datePicker', function(timeEntries) {
      return {
        scope: {
          date: '=',
          minDate: '=?',
          maxDate: '=?',
          callback: '=?'
        },
        retrict: 'E',
        templateUrl: $static('/static/orchestra/timing/timecard/partials/date-picker.html'),
        link: function(scope, elem, attrs) {
          var picker = new Pikaday({
            field: elem.get(0),
            minDate: scope.minDate,
            maxDate: scope.maxDate,
            onSelect: function(date) {
              scope.date = this.getMoment();
              if (typeof scope.callback === 'function') {
                scope.callback(date);
              }
              scope.$apply();
            }
          });

          scope.$watch(function() {
            return scope.minDate;
          }, function(newVal, oldVal) {
            if (newVal !== oldVal) {
              picker.setMinDate(newVal);
            }
          });
          scope.$watch(function() {
            return scope.maxDate;
          }, function(newVal, oldVal) {
            if (newVal !== oldVal) {
              picker.setMaxDate(newVal);
            }
          });
        }
      };
    })
    .directive('enforceIntegers', function(){
      // Non-digit chars are accepted in number inputs in some browsers (e.g., Safari)
      // Modified from stackoverflow.com/a/14425022
       return {
         scope: {
           max: '=?',
           min: '=?'
         },
         require: 'ngModel',
         link: function(scope, element, attrs, modelCtrl) {
           modelCtrl.$parsers.unshift(function(inputValue) {
             if (inputValue === undefined || inputValue === null) {
               modelCtrl.$setViewValue(0);
               modelCtrl.$render();
               return;
             }

             var transformedInput = String(inputValue).replace(/[^\d]/g, '');

             // Remove leading 0 if present
             if (transformedInput.length && transformedInput[0] === '0') {
               transformedInput = transformedInput.substring(1);
             }

             // Convert to integer
             if (transformedInput.length) {
               transformedInput = parseInt(transformedInput, 10);
               transformedInput = Math.min(transformedInput, scope.max);
               transformedInput = Math.max(transformedInput, scope.min);
             }
             else {
               transformedInput = 0;
             }

             if (transformedInput !== inputValue) {
               modelCtrl.$setViewValue(transformedInput);
               modelCtrl.$render();
             }

             return transformedInput;
           });
         }
       };
    });
})();
