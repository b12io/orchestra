import template from './todo-checklist.html'
import moment from 'moment-timezone'
import './todo-checklist.scss'

export default function todoChecklist () {
  return {
    template,
    restrict: 'E',
    scope: {
      title: '@',
      todos: '<',
      showChecked: '=',
      updateTodo: '=',
      steps: '<',
      taskSlugs: '<'
    },
    link: function (scope, elem, attrs) {
      const getLocalTime = (datetimeString) => {
        return datetimeString ? moment.utc(datetimeString).tz(moment.tz.guess()) : null
      }

      const getPrettyDatetime = (datetime) => {
        return datetime.format('ddd, MMM D h:mm a')
      }

      scope.getDatetimeDisplay = (datetimeString) => {
        const datetime = getLocalTime(datetimeString)
        const datetimeInfo = datetime ? `${getPrettyDatetime(datetime)}` : ''
        return datetimeInfo
      }

      scope.isNonEmptyString = (str) => {
        return str !== null && str !== undefined && str !== ''
      }
    }

  }
}
