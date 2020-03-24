import React from 'react';

import Switch from '@b12/metronome/components/form/switch/Switch.es6.js'
import Button from '@b12/metronome/components/form/button/Button.es6.js'

type Props = {

}

const Navbar = ({}: Props) => {
    return (
        <div>
            Orchestra
            <Switch selected={0}>
                <Button label='Active' />
                <Button label='Pending' />
                <Button label='Paused' />
                <Button label='Completed' /> 
            </Switch>
        </div>

    )
}

export default Navbar