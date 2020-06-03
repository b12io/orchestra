import React, { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import TasksList from '../../components/TasksList/TasksList'
import { fetchDashboardTasks } from 'state/slices/dashboardTasks'
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
  }, [dispatch])

  const activeTasks = useSelector(getActiveTasksSelector)
  const pendingTasks = useSelector(getPendingTasksSelector)
  const pausedTasks = useSelector(getPausedTasksSelector)
  const completedTasks = useSelector(getCompletedTasksSelector)
  const isLoading = useSelector(taskLoadingStateSelector)

  return (
    <div>
      <TasksList status='success' tasks={activeTasks} isLoading={isLoading} />
      <TasksList status='warning' tasks={pendingTasks} isLoading={isLoading} />
      <TasksList status='error' tasks={pausedTasks} isLoading={isLoading} />
      <TasksList status='default' tasks={completedTasks} isLoading={isLoading} />
    </div>
  )
}

export default Dashboard
