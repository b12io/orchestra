import React from 'react'
import { useParams } from 'react-router-dom'
import { lazy } from '@loadable/component'

const icon = 'ShuffleIcon'

const Task = () => {
  const { taskId } = useParams()
  const LoadableTaskComponent = lazy(() =>
    import('../../assets/ShuffleIcon')
  )
  return (
    <div>
      <React.Suspense fallback="Loading...">
        <LoadableTaskComponent />
      </React.Suspense>
    </div>
  )
}

export default Task
