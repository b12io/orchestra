import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux'

import Navbar from '../../components/navbar/Navbar'
import ProjectsList from '../../components/ProjectsList/ProjectsList'
import { fetchDashboardTasks } from '../../state/dashboardTasks'

const Dashboard = () => {
  const dispatch = useDispatch()

  useEffect(() => {
    dispatch(fetchDashboardTasks())
  }, [])

  return (
        <div>
            <Navbar />
            <ProjectsList status='success'/>
            <ProjectsList status='warning'/>
            <ProjectsList status='error'/>
            <ProjectsList status='default'/>
        </div>
    )
}

export default Dashboard;
