import axios from 'axios'
import { createSlice, PayloadAction } from '@reduxjs/toolkit'

import { AppThunk } from '../store'

interface Timer {
  id: number,
  start_time: string | null,
  stop_time: string | null,
  description: string | null,
  worker: number,
  assignment: number | null,
  time_worked: string
}

interface TimerState {
  status: Timer | null
}

const initialState: TimerState = {
  status: null
}

const timer = createSlice({
  name: 'timer',
  initialState,
  reducers: {
    getTimerStart(state) {
      // state.loading = true
      // state.error = null
    },
    getTimerSuccess(state, action: PayloadAction<Timer>) {
      state.status = action.payload
    },
    getTimerFailure(state, action: PayloadAction<string>) {
      // state.loading = false
      // state.error = action.payload
    }
  }
})

export default timer

export const fetchTimer = (): AppThunk => async dispatch => {
  try {
    dispatch(timer.actions.getTimerStart())
    const response = await axios.get('/orchestra/api/interface/timer/')
    const data: Timer = response.data
    dispatch(timer.actions.getTimerSuccess(data))
  } catch (err) {
    dispatch(timer.actions.getTimerFailure(err))
  }
}
