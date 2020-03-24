import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux'

import Navbar from '../../components/navbar/Navbar'
import ProjectsList from '../../components/ProjectsList/ProjectsList'
import { fetchDashboardTasks } from '../../state/dashboardTasks'
import { getActiveTasksSelector } from '../../state/selectors/taskSelectors'

const Dashboard = () => {
  const dispatch = useDispatch()

  useEffect(() => {
    dispatch(fetchDashboardTasks())
  }, [])

  const activeTasks = useSelector(getActiveTasksSelector)

  return (
    <div>
      <Navbar />
      <ProjectsList/>
    </div>
  )
}

export default Dashboard;
