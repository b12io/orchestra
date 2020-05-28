import { combineReducers } from '@reduxjs/toolkit'

import dashboardTasks from './slices/dashboardTasks'
import timer from './slices/timer'

const rootReducer = combineReducers({
  [dashboardTasks.name]: dashboardTasks.reducer,
  [timer.name]: timer.reducer
})

export type RootState = ReturnType<typeof rootReducer>

export default rootReducer
