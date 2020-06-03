## About The Project

This folder contains the new frontend app for Orchestra, created in React.

### Built With
* [create-react-app](https://create-react-app.dev/)
* [TypeScript](https://www.typescriptlang.org/)
* [Redux Toolkit](https://redux-toolkit.js.org/)

## Getting Started

To run this project, use `yarn watch`. The compiled files will be placed in `./orchestra/static/dist2/`.


## Usage

Use this space to show useful examples of how a project can be used. Additional screenshots, code examples and demos work well in this space. You may also link to more resources.


## Data Modelling with Redux Tookit

We use slices for each feature that requires the state to be saved in Redux. Each slice represents a piece of related information. As an example, the timer slice, where all timer-related actions and and slice information lives in the `/state/slice/timer.ts` file. Selectors will live in the `/state/selectors/` folder. 
