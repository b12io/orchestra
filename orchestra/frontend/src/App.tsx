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
              <Link to="/task/5">Task</Link>
            </li>
          </ul>
          <Switch>
            <Route path="/task/:taskId" children={<Task />} />
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
