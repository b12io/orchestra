import { createSelector } from 'reselect'

import { RootState } from '../rootReducer'

export enum TaskStates {
  JustAdded = 'just_added',
  InProgress = 'in_progress',
  Returned = 'returned',
  PendingReview = 'pending_review',
  PendingProcessing = 'pending_processing',
  Paused = 'paused',
  Complete = 'complete'
}

const ACTIVE_TASK_STATES = [
  TaskStates.JustAdded,
  TaskStates.InProgress,
  TaskStates.Returned
]

const PENDING_TASK_STATES = [
  TaskStates.PendingReview,
  TaskStates.PendingProcessing
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
    task => (ACTIVE_TASK_STATES.includes(task.state) && !task.should_be_active) ||
      PENDING_TASK_STATES.includes(task.state)
  )
)

export const getPausedTasksSelector = createSelector(
  tasksSelector,
  tasks => tasks.filter(task => task.state === TaskStates.Paused)
)

export const getCompletedTasksSelector = createSelector(
  tasksSelector,
  tasks => tasks.filter(task => task.state === TaskStates.Complete)
)

export const taskLoadingStateSelector = (state: RootState) => state.dashboardTasks.loading
