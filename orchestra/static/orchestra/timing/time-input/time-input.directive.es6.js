import template from './time-input.html'
import './time-input.scss'
// import moment from 'moment-timezone'

export default function timeInput () {
  return {
    template,
    scope: {
      datetime: '=',
      timeDisplay: '=?',
      onChange: '=?'
    },
    link: (scope) => {
      scope.datetime.seconds(0)
      scope.datetime.milliseconds(0)
      scope.timeDisplay = scope.datetime.toDate()
      scope.onChange = () => {
        scope.datetime.hours(scope.timeDisplay.getHours())
        scope.datetime.minutes(scope.timeDisplay.getMinutes())
      }
    }
  }
}
