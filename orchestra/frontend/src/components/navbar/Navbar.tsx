import React from 'react';

import AvatarItem from '@b12/metronome/components/layout/avatar/AvatarItem.es6.js'
import Button from '@b12/metronome/components/form/button/Button.es6.js'
import Grid from '@b12/metronome/components/layout/grid/Grid.es6.js'
import SimpleCard from '@b12/metronome/components/layout/simple-card/SimpleCard.es6.js'
import Switch from '@b12/metronome/components/form/switch/Switch.es6.js'
import TextField from '@b12/metronome/components/form/textfield/TextField.es6.js'

import { Clock, CaretDown } from '@b12/metronome/components/Icons.es6.js'

import './Navbar.scss'

import ShuffleIcon from '../../assets/ShuffleIcon'

const Navbar = () => {
    return (
        <div className="navbar">
            <Grid>
                <div className="navbar__title align-row">
                    <ShuffleIcon />
                    <h4>Orchestra</h4>
                </div>
                <Switch selected={0}>
                    <Button label="Active" />
                    <Button label="Pending" />
                    <Button label="Paused" />
                    <Button label="Completed" /> 
                </Switch>
                <div className="navbar__textfield">
                    <TextField 
                        placeholder="Search projects..."
                        searchIcon
                    />
                </div>
                <div className="navbar__timecard align-row">
                    <Clock />
                    <p>2h 15m</p>
                </div>
                <div className="navbar__avatar align-row">
                    <AvatarItem
                        primaryText="Adam Marcus"
                    />
                    <CaretDown />
                </div>
            </Grid>
        </div>
    )
}

export default Navbar