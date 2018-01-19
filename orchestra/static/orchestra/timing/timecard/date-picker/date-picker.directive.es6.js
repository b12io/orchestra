import Pikaday from 'pikaday'
import 'pikaday/scss/pikaday.scss'

import template from './date-picker.html'

export default function datePicker (timeEntries) {
  return {
    template,
    scope: {
      date: '=',
      minDate: '=?',
      maxDate: '=?',
      callback: '=?'
    },
    retrict: 'E',
    link: function (scope, elem, attrs) {
      var picker = new Pikaday({
        field: elem.get(0),
        minDate: scope.minDate ? scope.minDate.toDate() : null,
        maxDate: scope.maxDate ? scope.maxDate.toDate() : null,
        onSelect: function (date) {
          const newDate = this.getMoment()

          // Don't overwrite time when the date changes.
          if (!scope.date) {
            scope.date = newDate
          } else {
            scope.date.year(newDate.year())
              .month(newDate.month())
              .date(newDate.date())
          }
          if (typeof scope.callback === 'function') {
            scope.callback(scope.date)
          }
          scope.$apply()
        }
      })

      scope.$watch(function () {
        return scope.minDate
      }, function (newVal, oldVal) {
        if (newVal !== oldVal) {
          picker.setMinDate(newVal)
        }
      })
      scope.$watch(function () {
        return scope.maxDate
      }, function (newVal, oldVal) {
        if (newVal !== oldVal) {
          picker.setMaxDate(newVal)
        }
      })
    }
  }
}
