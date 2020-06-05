import React from 'react'
import { useParams } from 'react-router-dom'

const Task = () => {
  const { taskId } = useParams()
  const LoadableTaskComponent = window.orchestra?.tasks
  return (
    <div>
      {LoadableTaskComponent && <LoadableTaskComponent />}
    </div>
  )
}

export default Task
