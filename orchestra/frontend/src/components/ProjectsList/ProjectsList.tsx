import React from 'react';
import {
  Link
} from "react-router-dom"

import './ProjectsList.scss'

import Table from '@b12/metronome/components/layout/table/Table.es6'
import TableHead from '@b12/metronome/components/layout/table/TableHead.es6'
import TableBody from '@b12/metronome/components/layout/table/TableBody.es6'
import TableRow from '@b12/metronome/components/layout/table/TableRow.es6'
import TableCell from '@b12/metronome/components/layout/table/TableCell.es6'

type Props = {

}

const ProjectList = ({}: Props) => {
  const rowsLabels = [
    'Status',
    'Project and task',
    'Next steps',
    'Assigned',
    'Start by',
    'Due by'
  ]
  const data = [
    {
      id: 3,
      status: 'Rocky Mountain Tracking',
      project: 'Launch v4',
      task: 'Customer success',
      nextStep:'Kickoff call',
      assignedDate: '2 weeks ago',
      startBy: 'Today, 8:00 am',
      dueBy: '-'
    },
    {
      id: 4,
      status: 'Rocky Mountain Tracking',
      project: 'Launch v4',
      task: 'Customer success',
      nextStep:'Kickoff call',
      assignedDate: '2 weeks ago',
      startBy: 'Today, 8:00 am',
      dueBy: '-'
    },
    {
      id: 5,
      status: 'Rocky Mountain Tracking',
      project: 'Launch v4',
      task: 'Customer success',
      nextStep:'Kickoff call',
      assignedDate: '2 weeks ago',
      startBy: 'Today, 8:00 am',
      dueBy: '-'
    },
    {
      id: 6,
      status: 'Rocky Mountain Tracking',
      project: 'Launch v4',
      task: 'Customer success',
      nextStep:'Kickoff call',
      assignedDate: '2 weeks ago',
      startBy: 'Today, 8:00 am',
      dueBy: '-'
    },
  ]
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
          {rowsLabels.map(rowLabel => (
              <TableCell
              key={rowLabel}
              align='left'
              ><p>{rowLabel}</p></TableCell>
          ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map(row => (
            <TableRow key={row.id}>
              <TableCell><Link to={`/task/${row.id}`}><p>{row.status}</p></Link></TableCell>
              <TableCell><p>{row.project} / {row.task}</p></TableCell>
              <TableCell><p>{row.nextStep}</p></TableCell>
              <TableCell><p>{row.assignedDate}</p></TableCell>
              <TableCell><p>{row.startBy}</p></TableCell>
              <TableCell><p>{row.dueBy}</p></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>

  )
}

export default ProjectList
