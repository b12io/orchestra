import React from 'react';
import logo from './logo.svg';

import Button from '@b12/metronome/components/form/button/Button.es6'
import './App.scss';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
        <Button label="abcs" primary />
        Hello world!!??!?!?!??
      </header>
    </div>
  );
}

export default App;
