const path = require('path');
const { override, babelInclude } = require('customize-cra');

module.exports = override(
  babelInclude([
    // TODO(elstonayx): Remove customize-cra after compiling and exporting metronome as a proper package.
    // This temporarily fixes the usage of metronome, as cra does not compile files in node modules, and 
    // the metronome design system has not been compiled before exporting.
    path.resolve('node_modules/@b12/metronome'),
    path.resolve('src/')
  ])
)

