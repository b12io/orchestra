const path = require('path')
const ExtractTextPlugin = require('extract-text-webpack-plugin')

module.exports = {
  resolve: {
    modules: [
      'node_modules',
      path.join(__dirname, 'orchestra/static')
    ]
  },
  entry: {
    main: path.join(__dirname, 'orchestra/static/orchestra/main.es6.js')
  },
  output: {
    path: path.join(__dirname, 'orchestra/static/dist'),
    filename: '[name].js'
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: [/\.es6\.js$/, /node_modules/, /.*\.min\.js/],
        use: 'jshint-loader',  // Only works for ES5
        enforce: 'pre'
      }, {
        test: /\.es6\.js$/,
        exclude: [/node_modules/, /.*\.min\.js/],
        use: 'eslint-loader',  // Only works for ES6
        enforce: 'pre'
      }, {
        test: /\.html/,
        use: 'htmlhint-loader',
        exclude: /node_modules/,
        enforce: 'pre'
      }, {
        test: /\.json$/,
        use: 'json-loader'
      }, {
        test: /\.html$/,
        use: 'html-loader'
      }, {
        test: /.js$/,
        use: 'babel-loader',
        exclude: [/node_modules/, /.*\.min\.js/]
      }, {
        test: /\.s?css$/,
        use: ExtractTextPlugin.extract({
          fallback: 'style-loader',
          use: ['css-loader', 'sass-loader']
        })
      }
    ]
  },
  plugins: [
    new ExtractTextPlugin('[name].css')
  ],
  externals: {
    jQuery: 'jquery',
    $: 'jquery',
    'window.jQuery': 'jquery',
    angular: 'angular'
  },
  stats: {
    children: false
  },
  bail: true
}
