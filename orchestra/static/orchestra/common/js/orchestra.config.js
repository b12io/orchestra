(function() {
  'use strict';

  angular
    .module('orchestra.config')
    .config(config);

  config.$inject = ['$locationProvider'];

  /**
   * @name config
   * @desc Enable HTML5 routing
   */
  function config($locationProvider) {
    $locationProvider.html5Mode(true);
    $locationProvider.hashPrefix('!');
  }
})();
