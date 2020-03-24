const path = require('path');
const { override, babelInclude } = require('customize-cra');

module.exports = override(
  babelInclude([
    path.resolve('node_modules/@b12/metronome'),
    path.resolve('src/')
  ])
)

