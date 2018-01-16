import template from './time-input.html'
import './time-input.scss'

export default function timeInput () {
  return {
    template,
    scope: {
      datetime: '=',
      defaultHour: '@?'
    },
    link: (scope, elem, attrs) => {
      if (!scope.defaultHour) {
        scope.defaultHour = 8
      }
      scope.onChange = () => {
        scope.datetime.hours(scope.timeDisplay.getHours())
        scope.datetime.minutes(scope.timeDisplay.getMinutes())
      }

      scope.$watch(() => {
        return scope.datetime
      }, () => {
        if (scope.datetime) {
          if (!scope.datetime.hours() && !scope.datetime.minutes()) {
            scope.datetime.hours(scope.defaultHour)
          }
          scope.datetime.seconds(0)
          scope.datetime.milliseconds(0)
          scope.timeDisplay = scope.datetime.toDate()
        } else {
          scope.timeDisplay = null
        }
      })
    }
  }
}
