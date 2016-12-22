import moment from 'moment-timezone'

export default function timeEntries ($http, TimeEntry) {
  /**
   * Manage time tracking data for an Orchestra user.
   */
  'ngAnnotate'
  var timeEntries = {
    apiUrl: '/orchestra/api/interface/time_entries/',
    entries: [],
    entriesByDate: {},
    data: null,

    /**
     * Get worker time entries for the provided date range (inclusive).
     */
    updateEntries: function (minDate, maxDate) {
      var service = this

      // Remove time component from dates
      service.minDate = minDate.startOf('day')
      service.maxDate = maxDate.startOf('day')

      service.data = $http.get(service.apiUrl, {
        params: {
          min_date: service.minDate.format('YYYY-MM-DD'),
          max_date: service.maxDate.format('YYYY-MM-DD')
        }
      })
      .then(function (response) {
        // Initialize dates in range
        var numDays = maxDate.diff(minDate, 'days')
        service.entriesByDate = {}
        for (var i = 0; i < numDays + 1; i++) {
          var date = minDate.clone().add(i, 'days')
          service.entriesByDate[service.keyForDate(date)] = []
        }

        // Add newly filtered entries
        response.data.forEach(function (entryData) {
          service.addEntry(entryData)
        })
      }, function () {
        window.alert('Could not retrieve time entries')
      })
    },

    /**
     * Creates a new TimeEntry server-side and initializes with returned data.
     */
    createEntry: function (date) {
      var service = this

      var createUrl = '/orchestra/api/interface/time_entries/'
      this.date = date || moment()
      return $http.post(createUrl, {
        date: date.format('YYYY-MM-DD'),
        time_worked: moment.duration().stamp()
      })
      .then(function (response) {
        return service.addEntry(response.data)
      }, function (entry) {
        window.alert('Could not add new time entry.')
      })
    },

    /**
     * Calculate the total work time for a given date.
     */
    timeWorkedForDate: function (date) {
      var entries = this.entriesByDate[this.keyForDate(date)]
      var totalDuration = moment.duration()
      entries.forEach(function (entry) {
        if (entry.time_worked) {
          totalDuration.add(entry.time_worked.roundMinute())
        }
      })
      return totalDuration
    },

    /**
     * Determines the number of incomplete entries for a given date.
     */
    invalidEntriesForDate: function (date) {
      var entries = this.entriesByDate[this.keyForDate(date)]
      var invalid = []
      entries.forEach(function (entry) {
        if (entry.isIncomplete()) {
          invalid.push(entry)
        }
      })
      return invalid
    },

    /**
     * Determines the total number of incomplete entries.
     */
    invalidEntries: function () {
      var invalid = []
      for (var date in this.entriesByDate) {
        invalid = invalid.concat(this.invalidEntriesForDate(date))
      }
      return invalid
    },

    /**
     * Helpers for adding and deleting time entries.
     */
    addEntry: function (data) {
      var entry = new TimeEntry(data)
      this.entries.push(entry)
      this.addEntryToDate(entry, entry.date)
      return entry
    },
    deleteEntry: function (entry) {
      if (window.confirm('Are you sure you want to delete this entry?')) {
        entry.delete()
        this.removeEntryFromDate(entry, entry.date)
        this.entries.splice(this.entries.indexOf(entry), 1)
      }
    },

    /**
     * Helpers for organizing time entry data by date.
     */
    keyForDate: function (date) {
      if (!moment.isMoment(date)) {
        date = moment(date)
      }
      return date.startOf('day').toISOString()
    },
    addEntryToDate: function (entry, date) {
      var dateISO = this.keyForDate(date)
      if (this.entriesByDate[dateISO] === undefined) {
        this.entriesByDate[dateISO] = []
      }
      this.entriesByDate[dateISO].push(entry)
    },
    removeEntryFromDate: function (entry, date) {
      var dateISO = this.keyForDate(date)
      var index = this.entriesByDate[dateISO].indexOf(entry)
      this.entriesByDate[dateISO].splice(index, 1)
    },
    moveToDate: function (entry, newDate) {
      this.removeEntryFromDate(entry, entry.date)
      this.addEntryToDate(entry, newDate)
      entry.date = newDate
    }
  }

  // Default filtered view is the past week of time entries
  let minDate = moment().startOf('isoWeek')
  let maxDate = moment().startOf('day')
  timeEntries.updateEntries(minDate, maxDate)
  return timeEntries
}
