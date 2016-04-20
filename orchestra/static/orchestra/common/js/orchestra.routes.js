(function() {
  'use strict';

  angular
    .module('orchestra.routes')
    .config(config);

  config.$inject = ['$routeProvider'];

  /**
   * @name config
   * @desc Define valid application routes
   */
  function config($routeProvider) {
    $routeProvider.when('/', {
        title: 'Dashboard',
        controller: 'DashboardController',
        controllerAs: 'vm',
        templateUrl: $static('/static/orchestra/dashboard/partials/dashboard.html')
      })
      .when('/performance/', {
        title: 'Performance',
        controller: 'PerformanceController',
        controllerAs: 'vm',
        templateUrl: $static('/static/orchestra/dashboard/partials/performance.html')
      })
      .when('/task/:taskId', {
        title: 'Task',
        controller: 'TaskController',
        controllerAs: 'vm',
        templateUrl: $static('/static/orchestra/task/partials/task.html')
      })
      .when('/project/:projectId', {
        title: 'Project',
        controller: 'ProjectManagementController',
        controllerAs: 'vm',
        templateUrl: $static('/static/orchestra/project_management/partials/project_management.html')
      })
      .when('/timecard/:taskId?', {
        title: 'Timecard',
        controller: 'TimecardController',
        controllerAs: 'vm',
        templateUrl: $static('/static/orchestra/timing/timecard/partials/timecard.html')
      })
      .otherwise('/');
  }
})();
