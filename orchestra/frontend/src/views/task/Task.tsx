import React from 'react'
import { useParams } from 'react-router-dom'
import store from '../../state/store'

window.ReactOrchestra = require('react')

const Task = () => {
  const { taskId } = useParams()
  const LoadableTaskComponent = window.orchestra?.task
  return (
    <div>
      {LoadableTaskComponent && <LoadableTaskComponent store={store} />}
    </div>
  )
}

export default Task
