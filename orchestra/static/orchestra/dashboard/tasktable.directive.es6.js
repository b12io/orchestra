import template from './tasktable.html'
import './tasktable.scss'
import moment from 'moment-timezone'

export default function tasktable () {
  'ngAnnotate'

  return {
    template,
    restrict: 'A',
    scope: {
      tasktable: '=',
      collapsed: '=?'
    },
    controllerAs: 'vm',
    bindToController: true,
    controller: function ($location, $timeout, $window, orchestraTasks) {
      const vm = this
      vm.openTask = (task) => {
        $window.open(`task/${task.id}`, '_blank')
      }
      // Surface service to interpolator
      vm.orchestraTasks = orchestraTasks

      vm.waiting = true
      orchestraTasks.data.finally(() => {
        vm.waiting = false
        vm.showTagsCol = vm.tasktable.tasks.some(task => task.tags.length > 0)
      })
      vm.isInDanger = (task) => {
        return moment.isBeforeNowBy(task.next_todo_dict.due_datetime, 0, 'days')
      }

      vm.toggleCollapsed = () => {
        vm.collapsed = !vm.collapsed
      }

      vm.getDatetimeFormat = (datetimeString) => {
        const localTime = datetimeString ? moment.utc(datetimeString).tz(moment.tz.guess()) : null
        if (localTime && localTime.isSame(new Date(), 'day')) {
          return '[Today], h:mm a'
        }
        return null
      }
    }
  }
}
