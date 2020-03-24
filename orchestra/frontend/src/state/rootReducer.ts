import { combineReducers } from '@reduxjs/toolkit'

import dashboardTasks from './dashboardTasks'
import timer from './timer'

const rootReducer = combineReducers({
  [dashboardTasks.name]: dashboardTasks.reducer,
  [timer.name]: timer.reducer
})

export type RootState = ReturnType<typeof rootReducer>

export default rootReducer
