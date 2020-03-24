import { createSelector } from 'reselect'

import { RootState } from '../rootReducer'

export const tasksSelector = (state: RootState) => state.dashboardTasks.tasks

export const getActiveTasksSelector = createSelector(
  tasksSelector,
  tasks => tasks.filter(task => task.state === 'in_progress')
)

