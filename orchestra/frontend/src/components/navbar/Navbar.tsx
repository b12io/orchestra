import React, { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import { useHistory } from 'react-router-dom'

import AvatarItem from '@b12/metronome/components/layout/avatar/AvatarItem.es6.js'
import Grid from '@b12/metronome/components/layout/grid/Grid.es6.js'
import { Clock, CaretDown } from '@b12/metronome/components/Icons.es6.js'
import Dropdown from '@b12/metronome/components/layout/dropdown/Dropdown.es6.js'
import DropdownItem from '@b12/metronome/components/layout/dropdown/DropdownItem.es6.js'

import './Navbar.scss'

import ShuffleIcon from 'assets/ShuffleIcon'
import { fetchTimer } from 'state/slices/timer'

const Navbar = () => {
  const history = useHistory()
  const dispatch = useDispatch()

  useEffect(() => {
    dispatch(fetchTimer())
  }, [])

  const handleHomeClick = () => {
    history.push('/')
  }

  return (
    <div className="navbar">
      <Grid>
        <div className="navbar__home align-row" onClick={handleHomeClick}>
          <ShuffleIcon />
          <h4>Orchestra</h4>
        </div>
        <div className="navbar__timecard align-row">
          <Clock />
          <p>2h 15m</p>
        </div>
        <Dropdown
          className="navbar__dropdown"
          simple
          toggle={
            <div className="navbar__avatar align-row">
              <AvatarItem primaryText="Elston Aijan" />
              <CaretDown className="navbar__avatar-caret"/>
            </div>}>
          <DropdownItem
            label="Dashboard"
            onClick={() => { history.push('/') }}
          />
          <DropdownItem
            label="Timecard"
            onClick={() => { history.push('/timecard/') }}
          />
          <DropdownItem
            label="Available tasks"
            onClick={() => { history.push('/communication/available-staffing-requests') }}
          />
          <DropdownItem
            label="Project management"
            onClick={() => { history.push('/project/') }}
          />
          <DropdownItem
            label="Account settings"
            onClick={() => { history.push('/accounts/settings') }}
          />
          <DropdownItem
            label="Sign out"
            onClick={() => { history.push('/accounts/logout_then_login') }}
          />
        </Dropdown>
      </Grid>
    </div>
  )
}

export default Navbar
