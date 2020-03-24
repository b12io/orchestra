import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux'

import ProjectsList from '../../components/ProjectsList/ProjectsList'
import { fetchDashboardTasks } from '../../state/dashboardTasks'
import {
    getActiveTasksSelector,
    getPendingTasksSelector,
    getPausedTasksSelector,
    getCompletedTasksSelector,
    taskLoadingStateSelector
} from '../../state/selectors/taskSelectors'

const Dashboard = () => {
  const dispatch = useDispatch()

  useEffect(() => {
    dispatch(fetchDashboardTasks())
  }, [])

  const activeTasks = useSelector(getActiveTasksSelector)
  const pendingTasks = useSelector(getPendingTasksSelector)
  const pausedTasks = useSelector(getPausedTasksSelector)
  const completedTasks = useSelector(getCompletedTasksSelector)
  const isLoading = useSelector(taskLoadingStateSelector)

  return (
    <div>
      <ProjectsList status='success' projects={activeTasks} isLoading={isLoading} />
      <ProjectsList status='warning' projects={pendingTasks} isLoading={isLoading} />
      <ProjectsList status='error' projects={pausedTasks} isLoading={isLoading} />
      <ProjectsList status='default' projects={completedTasks} isLoading={isLoading} />
    </div>
  )
}

export default Dashboard;
