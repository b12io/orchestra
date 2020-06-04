import React from 'react'
import { useParams } from 'react-router-dom'

const Task = () => {
  const { taskId } = useParams()
  const LoadableTaskComponent = window.orchestra?.tasks
  return (
    <div>
      <LoadableTaskComponent id={taskId} />
    </div>
  )
}

export default Task
