import React from 'react';
import {
  useHistory
} from "react-router-dom"

import './TasksList.scss'

import Table from '@b12/metronome/components/layout/table/Table.es6'
import TableHead from '@b12/metronome/components/layout/table/TableHead.es6'
import TableBody from '@b12/metronome/components/layout/table/TableBody.es6'
import TableRow from '@b12/metronome/components/layout/table/TableRow.es6'
import TableCell from '@b12/metronome/components/layout/table/TableCell.es6'
import Badge from '@b12/metronome/components/layout/badge/Badge.es6.js'
import StatusIndicator from '@b12/metronome/components/layout/status-indicator/StatusIndicator.es6.js'

import AnimatedCircle from '../../assets/AnimatedCircle'

type ProjectListProps = {
  status: any,
  tasks: any,
  isLoading?: boolean
}

const TaskList = ({ status, tasks, isLoading = false }: ProjectListProps) => {
  const rowsLabels = [
    'Status',
    'Project / Task',
    'Next steps',
    'Assigned',
    'Start by',
    'Due by'
  ]
  const history = useHistory()

  const renderTasks = () => {
    return tasks.map(row => (
      <TableRow key={row.id} onClick={() => history.push(`/task/${row.id}`)}>
        <TableCell>
          <h4>{row.detail}</h4>
          <Badge size="medium" label="Iterating" primary filled className='dsu-mr-xxxsm'/>
          <Badge size="medium" label="SEO" filled neutral/>
        </TableCell>
        <TableCell><p>{row.project} / {row.step}</p></TableCell>
        {/* change to next_todo_dict */}
        <TableCell><p>{row.step}</p></TableCell>
        <TableCell><p>2 weeks ago</p></TableCell>
        <TableCell><p>Today, 8:00 am</p></TableCell>
        <TableCell><p>-</p></TableCell>
        {/* <TableCell><p>{row.assignedDate}</p></TableCell>
        <TableCell><p>{row.startBy}</p></TableCell>
        <TableCell><p>{row.dueBy}</p></TableCell> */}
      </TableRow>
    ))
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
            <TableCell className='tasks-list__status-row'>
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
            </TableCell>
            <TableCell/>
            <TableCell/>
            <TableCell/>
            <TableCell/>
            <TableCell/>
          </TableRow>
        </TableHead>
        <TableHead>
          <TableRow>
            {rowsLabels.map(rowLabel => (
              <TableCell
                key={rowLabel}
                align='left'
              ><p>{rowLabel}</p></TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {tasks.length !== 0 || isLoading
            ? renderTasks()
            : renderEmptyList()}
        </TableBody>
      </Table>
    </div>

  )
}

export default TaskList
