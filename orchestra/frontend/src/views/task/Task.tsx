import React from 'react'
import {
  useParams
} from 'react-router-dom'

const Task = () => {
  const { taskId } = useParams();
  return (
        <div>
          Task view: { taskId }
        </div>
    )
}

export default Task;
