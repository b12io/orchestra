(function() {
  'use strict';

  angular.module('orchestra.timing')
    .directive('pikaday', function(timeEntries) {
      return {
        scope: {
          entry: '=',
        },
        retrict: 'A',
        link: function(scope, elem, attrs) {
          var picker = new Pikaday({
            field: elem.get(0),
            minDate: moment().subtract(1, 'week').toDate(),
            maxDate: moment().toDate(),
            onSelect: function(date) {
              timeEntries.moveToDate(scope.entry, this.getMoment());
              scope.$apply();
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
           digits: '=?',
         },
         require: 'ngModel',
         link: function(scope, element, attrs, modelCtrl) {
           scope.digits = scope.digits || 2;

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

             // Truncate to correct number of digits
             transformedInput = transformedInput.substring(0, scope.digits);

             // Convert to integer
             if (transformedInput.length) {
               transformedInput = parseInt(transformedInput, 10);
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
