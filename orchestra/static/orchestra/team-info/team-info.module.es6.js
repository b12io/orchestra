/* global angular */

import common from 'orchestra/common/common.module.es6.js'
import teamInfoCard from 'orchestra/team-info/team-info-card.directive.es6.js'

const name = 'orchestra.teamInfo'
angular.module(name, ['ui.select', 'ngSanitize', common])
  .directive('teamInfoCard', teamInfoCard)

export default name
