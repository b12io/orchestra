import moment from 'moment-timezone'

export const getLocalTime = (datetimeString) => {
  return datetimeString ? moment.utc(datetimeString).tz(moment.tz.guess()) : null
}

export const specialFormatIfToday = (datetimeString) => {
  const localTime = datetimeString ? moment.utc(datetimeString).tz(moment.tz.guess()) : null
  if (localTime && localTime.isSame(new Date(), 'day')) {
    return '[Today], h:mm a'
  }
  return null
}

export const getPrettyDatetime = (datetimeString, customFormat=null, showTime=false) => {
  const datetime = getLocalTime(datetimeString)
  if (datetime === null) {
    return null
  } else if (customFormat) {
    return datetime.format(customFormat)
  } else if (showTime) {
    return datetime.format('ddd, MMM D h:mm a')
  } else {
    return datetime.format('ddd, MMM D')
  }
}

export const isOutdated = (datetimeString) => {
  const now = moment().utc()
  return now.isAfter(datetimeString)
}
