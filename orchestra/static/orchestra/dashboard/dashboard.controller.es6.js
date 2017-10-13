import './dashboard.scss'

export default function DashboardController (
      orchestraTasks) {
  'ngAnnotate'
  var vm = this

  vm.orchestraTasks = orchestraTasks
  orchestraTasks.updateTasks()
}
