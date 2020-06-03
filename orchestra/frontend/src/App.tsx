import React from 'react'
import {
  HashRouter as Router,
  Switch,
  Route,
} from 'react-router-dom'

import Navbar from './components/navbar/Navbar'
import AvailableTasks from './views/available_tasks/AvailableTasks'
import Dashboard from './views/dashboard/Dashboard'
import Task from './views/task/Task'

import './App.scss'

function App () {
  return (
    <div className="App">
      <Router>
        <div>
          <Navbar />
          <Switch>
            <Route path="/task/:taskId" children={<Task />} />
            <Route path="/project/:projectId?" children={<div>Project management</div>} />
            <Route path="/timecard" children={<div>Timecard</div>} />
            <Route path="/communication/available-staffing-requests" children={<AvailableTasks />} />
            <Route path="/accounts/settings" children={<div>Account settings</div>} />
            <Route path="/accounts/logout_then_login" children={<div>Sign out</div>} />
            <Route path="/" children={<Dashboard />} />
          </Switch>
        </div>
      </Router>
    </div>
  );
}

export default App
