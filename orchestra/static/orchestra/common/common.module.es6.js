/* global angular */

import orchestraApi from 'orchestra/common/js/orchestra_api.es6.js'
import helpers from 'orchestra/common/js/helpers.es6.js'
import {
  orchestraService,
  orchestraTasks
} from 'orchestra/common/js/orchestra.services.es6.js'
import {
  capitalize,
  toArray
} from 'orchestra/common/js/orchestra.filters.es6.js'

import orchestraChecklist from 'orchestra/common/components/checklist/checklist.directive.es6.js'
import orchestraChecklistItem from 'orchestra/common/components/checklist/checklist-item.directive.es6.js'
import orchestraQuill from 'orchestra/common/components/quill/quill.directive.es6.js'
import orchestraTeamMessages from 'orchestra/common/components/team-messages/team-messages.directive.es6.js'
import projectFolder from 'orchestra/common/components/project-folder/project-folder.directive.es6.js'
import websiteIframe from 'orchestra/common/components/website-iframe/website-iframe.directive.es6.js'

const name = 'orchestra.common'
angular.module('orchestra.common', [])
  .factory('orchestraService', orchestraService)
  .factory('orchestraTasks', orchestraTasks)
  .factory('orchestraApi', orchestraApi)
  .factory('helpers', helpers)
  .filter('capitalize', capitalize)
  .filter('toArray', toArray)

  .directive('orchestraChecklist', orchestraChecklist)
  .directive('orchestraChecklistItem', orchestraChecklistItem)
  .directive('orchestraQuill', orchestraQuill)
  .directive('orchestraTeamMessages', orchestraTeamMessages)
  .directive('projectFolder', projectFolder)
  .directive('websiteIframe', websiteIframe)

export default name
