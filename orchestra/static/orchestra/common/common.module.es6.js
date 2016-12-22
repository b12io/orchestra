/* global angular */

import orchestraApi from 'orchestra/common/js/orchestra_api.es6.js'
import {
  orchestraService,
  orchestraTasks
} from 'orchestra/common/js/orchestra.services.es6.js'
import {
  capitalize,
  toArray
} from 'orchestra/common/js/orchestra.filters.es6.js'

const name = 'orchestra.common'
angular.module('orchestra.common', [])
  .factory('orchestraService', orchestraService)
  .factory('orchestraTasks', orchestraTasks)
  .factory('orchestraApi', orchestraApi)
  .filter('capitalize', capitalize)
  .filter('toArray', toArray)

export default name
