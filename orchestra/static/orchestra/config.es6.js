import dashboardTemplate from 'orchestra/dashboard/partials/dashboard.html'
import taskTemplate from 'orchestra/task/task.html'
import projectManagementTemplate from 'orchestra/project_management/partials/project_management.html'
import timecardTemplate from 'orchestra/timing/timecard/partials/timecard.html'

/**
 * @name config
 * @desc Define valid application routes
 */
export default function config ($locationProvider, $routeProvider) {
  $locationProvider.html5Mode(true)
  $locationProvider.hashPrefix('!')

  $routeProvider.when('/', {
    title: 'Dashboard',
    controller: 'DashboardController',
    controllerAs: 'vm',
    template: dashboardTemplate
  }).when('/task/:taskId', {
    title: 'Task',
    controller: 'TaskController',
    controllerAs: 'vm',
    template: taskTemplate
  }).when('/project/:projectId?', {
    title: 'Project',
    controller: 'ProjectManagementController',
    controllerAs: 'vm',
    template: projectManagementTemplate
  }).when('/timecard/:taskId?', {
    title: 'Timecard',
    controller: 'TimecardController',
    controllerAs: 'vm',
    template: timecardTemplate
  }).otherwise('/')
}
