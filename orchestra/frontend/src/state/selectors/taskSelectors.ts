import { createSelector } from 'reselect'

import { RootState } from '../rootReducer'

const ACTIVE_TASK_STATES = [
  'just_added',
  'in_progress',
  'returned'
]

const PENDING_TASK_STATES = [
  'pending_review',
  'pending_processing'
]

export const tasksSelector = (state: RootState) => state.dashboardTasks.tasks

export const getActiveTasksSelector = createSelector(
  tasksSelector,
  tasks => tasks.filter(
    task => ACTIVE_TASK_STATES.includes(task.state) && task.should_be_active
  ) 
)

export const getPendingTasksSelector = createSelector(
  tasksSelector,
  tasks => tasks.filter(
    task => (ACTIVE_TASK_STATES.includes(task.state) && !task.should_be_active) 
      || PENDING_TASK_STATES.includes(task.state)
  )
)

export const getPausedTasksSelector = createSelector(
  tasksSelector,
  tasks => tasks.filter(task => task.state === 'paused')
)

export const getCompletedTasksSelector = createSelector(
  tasksSelector,
  tasks => tasks.filter(task => task.state === 'complete')
)
