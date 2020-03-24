import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux'

import Navbar from '../../components/navbar/Navbar'
import ProjectsList from '../../components/ProjectsList/ProjectsList'
import { fetchDashboardTasks } from '../../state/dashboardTasks'
import {
    getActiveTasksSelector,
    getPendingTasksSelector,
    getPausedTasksSelector,
    getCompletedTasksSelector
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

  return (
        <div>
            <Navbar />
            <ProjectsList status='success' projects={activeTasks}/>
            <ProjectsList status='warning' projects={pendingTasks}/>
            <ProjectsList status='error' projects={pausedTasks}/>
            <ProjectsList status='default' projects={completedTasks}/>
        </div>
    )
}

export default Dashboard;
