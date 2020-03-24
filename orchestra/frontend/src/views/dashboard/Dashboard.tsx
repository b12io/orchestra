import React from 'react';

import Navbar from '../../components/navbar/Navbar'
import ProjectsList from '../../components/ProjectsList/ProjectsList'

const Dashboard = () => {
    return (
        <div>
            <Navbar />
            <ProjectsList/>
        </div>
    )
}

export default Dashboard;
