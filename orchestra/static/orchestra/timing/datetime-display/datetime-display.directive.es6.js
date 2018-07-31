import template from './datetime-display.html'
import moment from 'moment-timezone'

export default function datetimeDisplay () {
  return {
    template,
    restrict: 'E',
    scope: {
      datetime: '=',
      showTime: '=',
      customFormat: '='
    },
    link: (scope, elem, attrs) => {
      const getLocalTime = (datetimeString) => {
        return datetimeString ? moment.utc(datetimeString).tz(moment.tz.guess()) : null
      }

      const getPrettyDatetime = (datetime) => {
        if (scope.customFormat) {
          return datetime.format(scope.customFormat)
        } else if (scope.showTime) {
          return datetime.format('ddd, MMM D h:mm a')
        } else {
          return datetime.format('ddd, MMM D')
        }
      }

      scope.getDatetimeDisplay = (datetimeString) => {
        const datetime = getLocalTime(datetimeString)
        const datetimeInfo = datetime ? `${getPrettyDatetime(datetime)}` : ''
        return datetimeInfo
      }
    }
  }
}
