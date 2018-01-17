/* global angular */

import common from 'orchestra/common/common.module.es6.js'

import datePicker from 'orchestra/timing/timecard/date-picker/date-picker.directive.es6.js'
import taskSelect from 'orchestra/timing/timecard/task-select/task-select.directive.es6.js'
import enforceIntegers from 'orchestra/timing/timecard/enforce-integers.directive.es6.js'
import TimecardController from 'orchestra/timing/timecard/timecard.controller.es6.js'
import workTimer from 'orchestra/timing/timer/timer.directive.es6.js'
import timeEntries from 'orchestra/timing/time-entries.service.es6.js'
import TimeEntry from 'orchestra/timing/time-entry.service.es6.js'
import timeInput from 'orchestra/timing/time-input/time-input.directive.es6.js'
import datetimeDisplay from 'orchestra/timing/datetime-display/datetime-display.directive.es6.js'

const name = 'orchestra.timing'
angular.module(name, ['ui.select', 'ngSanitize', common])
  .directive('datePicker', datePicker)
  .directive('taskSelect', taskSelect)
  .directive('enforceIntegers', enforceIntegers)
  .directive('workTimer', workTimer)
  .directive('timeInput', timeInput)
  .directive('datetimeDisplay', datetimeDisplay)
  .controller('TimecardController', TimecardController)
  .factory('timeEntries', timeEntries)
  .factory('TimeEntry', TimeEntry)
export default name
