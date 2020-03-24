import React from 'react';
import {
  useHistory
} from "react-router-dom"

import './ProjectsList.scss'

import Table from '@b12/metronome/components/layout/table/Table.es6'
import TableHead from '@b12/metronome/components/layout/table/TableHead.es6'
import TableBody from '@b12/metronome/components/layout/table/TableBody.es6'
import TableRow from '@b12/metronome/components/layout/table/TableRow.es6'
import TableCell from '@b12/metronome/components/layout/table/TableCell.es6'
import Badge from '@b12/metronome/components/layout/badge/Badge.es6.js'
import StatusIndicator from '@b12/metronome/components/layout/status-indicator/StatusIndicator.es6.js'

const ProjectList = (props) => {
  const rowsLabels = [
    'Status',
    'Project and task',
    'Next steps',
    'Assigned',
    'Start by',
    'Due by'
  ]
  const history = useHistory()
  const {
    status,
    projects
  } = props
  const renderProjects = () => {
    return projects.map(row => (
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
  return (
    <div className='projects-list__wrapper'>
      <Table
        padding='comfortable'
        verticalAlign='middle'
        className='projects-list'
        cardLike
      >
        <TableHead>
          <TableRow>
            <TableCell className='projects-list__status-row'>
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
              <p>{projects.length} project{projects.length !== 1 && 's'}</p>
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
          {projects.length !== 0
            ? renderProjects()
            : 'No projects'}
        </TableBody>
      </Table>
    </div>

  )
}

export default ProjectList
