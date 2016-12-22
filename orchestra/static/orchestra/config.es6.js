import dashboardTemplate from 'orchestra/dashboard/dashboard.html'
import taskTemplate from 'orchestra/task/task.html'
import timecardTemplate from 'orchestra/timing/timecard/timecard.html'
import projectManagementTemplate from 'orchestra/project-management/project-management.html'

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
