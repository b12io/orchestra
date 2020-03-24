import React from 'react'
import {
  HashRouter as Router,
  Switch,
  Route,
  Link
} from "react-router-dom"

import Dashboard from './views/dashboard/Dashboard'
import Task from './views/task/Task'

import './App.scss';

function App() {
  return (
    <div className="App">
      <Router>
        <div>
          <ul>
            <li>
              <Link to="/">Dashboard</Link>
            </li>
            <li>
              <Link to="/timecard">Timecard</Link>
            </li>
            <li>
              <Link to="/communication/available-staffing-requests">Available tasks</Link>
            </li>
            <li>
              <Link to="/project/">Project management</Link>
            </li>
            <li>
              <Link to="/accounts/settings">Account settings</Link>
            </li>
            <li>
              <Link to="/accounts/logout_then_login">Sign out</Link>
            </li>
          </ul>
          <Switch>
            <Route path="/task/:taskId" children={<Task />} />
            <Route path="/project/:projectId?" children={<div>Project management</div>} />
            <Route path="/timecard" children={<div>Timecard</div>} />
            <Route path="/communication/available-staffing-requests" children={<div>Available tasks</div>} />
            <Route path="/accounts/settings" children={<div>Account settings</div>} />
            <Route path="/accounts/logout_then_login" children={<div>Sign out</div>} />
            <Route path="/">
              <Dashboard />
            </Route>
          </Switch>
        </div>
      </Router>
    </div>
  );
}

export default App;
