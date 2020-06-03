import { Task } from 'state/slices/dashboardTasks'

export type SortStatus = {
  column: string | null;
  direction: 'ascending' | 'descending';
}

const TASK_LABEL_MAPPING = {
  'Details': 'detail',
  'Project / Task': 'project',
  'Assigned': 'assignment_start_datetime'
}

const SORT_ASCENDING = 1
const SORT_DESCENDING = -1

export const sortTasks = (tasks: Task[], sortStatus: SortStatus): Task[] => {
  const { column, direction } = sortStatus
  const sortedTasks = tasks
  sortedTasks.sort((firstTask, secondTask) => {
    const taskProperty = TASK_LABEL_MAPPING[column] ?? TASK_LABEL_MAPPING['Details']
    return firstTask[taskProperty].toLowerCase() > secondTask[taskProperty].toLowerCase()
      ? direction === 'ascending' ? SORT_ASCENDING : SORT_DESCENDING
      : direction === 'ascending' ? SORT_DESCENDING : SORT_ASCENDING
  })

  return sortedTasks
}
