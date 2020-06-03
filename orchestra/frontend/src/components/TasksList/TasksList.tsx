import React, { useState, useEffect } from 'react'
import {
  useHistory
} from 'react-router-dom'

import './TasksList.scss'

import Table from '@b12/metronome/components/layout/table/Table.es6'
import TableHead from '@b12/metronome/components/layout/table/TableHead.es6'
import TableBody from '@b12/metronome/components/layout/table/TableBody.es6'
import TableRow from '@b12/metronome/components/layout/table/TableRow.es6'
import TableCell from '@b12/metronome/components/layout/table/TableCell.es6'
import TextField from '@b12/metronome/components/form/textfield/TextField.es6.js'
import Badge from '@b12/metronome/components/layout/badge/Badge.es6.js'
import StatusIndicator from '@b12/metronome/components/layout/status-indicator/StatusIndicator.es6.js'
import {
  CaretDown
} from '@b12/metronome/components/Icons.es6.js'

import AnimatedCircle from '../../assets/AnimatedCircle'

import { getPrettyDatetime, specialFormatIfToday, isOutdated } from '../../util/time'
import { Task } from 'state/slices/dashboardTasks'

import { sortTasks, SortStatus } from './helpers'

type ProjectListProps = {
  status: any;
  tasks: Task[];
  isLoading?: boolean;
}

const TaskList = ({ status, tasks, isLoading = false }: ProjectListProps) => {
  const [sortStatus, setSortStatus] = useState<SortStatus>({
    column: null,
    direction: 'ascending'
  })
  const [taskList, setTaskList] = useState<Task[]>([])

  useEffect(() => {
    setTaskList(tasks)
  }, [tasks])

  const [searchedItem, setSearchedItem] = useState('')

  const handleTextChange = value => {
    setSearchedItem(value)
  }

  useEffect(() => {
    const results = tasks.filter(task => {
      const lowerCaseSearchedItem = searchedItem.toLocaleLowerCase()
      return task.detail.toLowerCase().includes(lowerCaseSearchedItem) ||
      task.project.toLowerCase().includes(lowerCaseSearchedItem) ||
      task.step.toLowerCase().includes(lowerCaseSearchedItem)
    })
    setTaskList(results)
  }, [searchedItem])

  const rowsLabels = [
    'Details',
    'Project / Task',
    'Assigned',
    'Next steps',
    'Start by',
    'Due by'
  ]
  // Map Orchestra tag values to Metronome badge color values.
  const tagMapping = {
    'default': 'primary',
    'primary': 'primary', // We'll add `selected` below to make it stand out.
    'success': 'success',
    'info': 'neutral',
    'warning': 'warning',
    'danger': 'warning' // We'll add `selected` below to make it stand out.
  }
  const history = useHistory()

  const renderTasks = () => {
    return taskList.map(row => {
      const assigned = getPrettyDatetime(row.assignment_start_datetime, 'MM/DD/YYYY')
      const startBy = getPrettyDatetime(
        row.next_todo_dict.start_by_datetime,
        specialFormatIfToday(row.next_todo_dict.start_by_datetime))
      const dueBy = getPrettyDatetime(
        row.next_todo_dict.due_datetime,
        specialFormatIfToday(row.next_todo_dict.due_datetime))

      const rowUrl = `/task/${row.id}`

      const handleRowClick = (event: MouseEvent) => {
        if (event.ctrlKey || event.metaKey) {
          window.open('/orchestra/newapp/#' + rowUrl, '_blank')
        } else {
          history.push(rowUrl)
        }
      }
      const colorRow = isOutdated(row.next_todo_dict.due_datetime) && row.state !== 'complete'
      return (
        <TableRow key={row.id} onClick={handleRowClick} className={colorRow && 'grey-out'}>
          <TableCell className='tasks-list__col-1'>
            <h4>{row.detail}</h4>
            {row.tags.map((tag, index) => {
              const colorProps = {
                [tagMapping[tag.status]]: true,
                selected: tag.status === 'danger' || tag.status === 'primary' // Make it darker.
              }
              return (
                <Badge
                  key={index}
                  size="small"
                  label={tag.label}
                  filled
                  className="dsu-mr-xxxsm"
                  {...colorProps}
                />
              )
            })}
          </TableCell>
          <TableCell className='tasks-list__col-2'><p>{row.project} / {row.step}</p></TableCell>
          <TableCell className='tasks-list__col-3'><p>{assigned}</p></TableCell>
          <TableCell className='tasks-list__col-4'><p>{row.next_todo_dict.description}</p></TableCell>
          <TableCell className='tasks-list__col-5'><p>{startBy}</p></TableCell>
          <TableCell><p>{dueBy}</p></TableCell>
        </TableRow>
      )
    })
  }

  const renderEmptyList = () => (
    <TableRow>
      <TableCell/>
      <TableCell/>
      <TableCell><p>No tasks</p></TableCell>
      <TableCell/>
      <TableCell/>
      <TableCell/>
    </TableRow>
  )

  const handleHeaderClick = (column) => {
    let direction
    if (column !== sortStatus.column) {
      direction = 'ascending'
    } else {
      direction = sortStatus.direction === 'ascending' ? 'descending' : 'ascending'
    }

    const newSortStatus = { direction, column }
    const sortedTasks = sortTasks(taskList, newSortStatus)

    setTaskList(sortedTasks)
    setSortStatus(newSortStatus)
  }

  const renderSortCaret = () => {
    return sortStatus.direction === 'ascending'
      ? <CaretDown />
      : <CaretDown className="caret-up" />
  }

  const numberOfTasksText = `${tasks.length} task${tasks.length > 1 ? 's' : ''}`

  return (
    <div className='tasks-list__wrapper'>
      <Table
        padding='compact'
        verticalAlign='middle'
        className='tasks-list'
        cardLike
      >
        <TableHead padding="compact">
          <TableRow>
            <th className='tasks-list__status-row'>
              <b><StatusIndicator
                status={status}
                className='dsu-mr-xxxsm'
                statusLabels={{
                  success: 'Active',
                  error: 'Paused',
                  default: 'Completed',
                  warning: 'Pending'
                }}
              /></b>
              {isLoading ? <AnimatedCircle /> : <p>{numberOfTasksText}</p>}
            </th>
            <th colSpan={2}/>
            <th colSpan={4}>
              <div className="navbar__textfield">
                <TextField
                  placeholder="Search projects..."
                  searchIcon
                  onUpdate={handleTextChange}
                  value={searchedItem}
                />
              </div>
            </th>
          </TableRow>
        </TableHead>
        <TableHead>
          <TableRow>
            {rowsLabels.map((rowLabel, index) => (
              <TableCell
                key={rowLabel}
                align='left'
                className={`tasks-list__col-${index + 1}`}
                onClick={() => handleHeaderClick(rowLabel)}
              >
                <div className="tasks-list__col-header">
                  <p>{rowLabel}</p>
                  {sortStatus.column === rowLabel && renderSortCaret()}
                </div>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {taskList.length !== 0 || isLoading
            ? renderTasks()
            : renderEmptyList()}
        </TableBody>
      </Table>
    </div>

  )
}

export default TaskList
