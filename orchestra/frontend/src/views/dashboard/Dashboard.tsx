import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux'

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
            <ProjectsList status='success'/>
            <ProjectsList status='warning'/>
            <ProjectsList status='error'/>
            <ProjectsList status='default'/>
        </div>
    )
}

export default Dashboard;
