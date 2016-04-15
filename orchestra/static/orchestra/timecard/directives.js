(function() {
  // 'use strict';

  angular.module('orchestra.timecard')
    .directive('pikaday', function(timecardService) {
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
              scope.entry.date = this.getMoment();
              timecardService.updateEntry(scope.entry);
              scope.$apply();
            }
          });
        }
      };
    });
})();
