(function() {
  'use strict';

  var path = require('path');
  var webpack = require('webpack');
  var ExtractTextPlugin = require('extract-text-webpack-plugin');

  module.exports = {
    entry: {
      main: path.join(__dirname, 'orchestra/static/orchestra/main.es6.js')
    },
    output: {
      path: path.join(__dirname, 'orchestra/static/dist'),
      filename: '[name].js',
    },
    module: {
      preLoaders: [{
        test: /\.js$/,
        exclude: [/\.es6\.js$/, /node_modules/, /.*\.min\.js/],
        loader: 'jshint'  // Only works for ES5
      }, {
        test: /\.es6\.js$/,
        exclude: [/node_modules/, /.*\.min\.js/],
        loader: 'eslint'  // Only works for ES6
      }],
      loaders: [{
        test: /\.json$/,
        loaders: ['json-loader'],
      }, {
        test: /\.html$/,
        loaders: ['html-loader'],
      }, {
        test: /\.es6\.js$/,
        loader: 'babel',
        exclude: [/node_modules/, /.*\.min\.js/],
        query: {
          presets: ['es2015'],
          plugins: [
            'transform-object-rest-spread',
            ['babel-plugin-transform-builtin-extend', {
              globals: ['Error']
            }]
          ]
        }
      }, {
        test: /\.js$/,
        loaders: ['ng-annotate'],
      }, {
        test: /\.s?css$/,
        loader: ExtractTextPlugin.extract('style-loader', 'css-loader!sass-loader')
      }
    ]},
    plugins: [
      new ExtractTextPlugin('[name].css')
    ],
    externals: {
      jQuery: 'jquery',
      $: 'jquery',
      'window.jQuery': 'jquery',
      angular: 'angular'
    },
    resolve: {
      root: [
        'orchestra/static'
      ]
    },
    browser: {
      fs: false,
    },
    node: {
      fs: 'empty',
    },
    bail: true,
  };
})();
