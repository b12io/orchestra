import { combineReducers } from '@reduxjs/toolkit'

import dashboardTasks from './dashboardTasks'

const rootReducer = combineReducers({
  [dashboardTasks.name]: dashboardTasks.reducer
})

export type RootState = ReturnType<typeof rootReducer>

export default rootReducer
