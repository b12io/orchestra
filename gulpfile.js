(function() {
  'use strict';
  // utils
  var gulp = require('gulp');
  var argv = require('yargs').argv;
  var cache = require('gulp-cached');
  var print = require('gulp-print');
  var rename = require('gulp-rename');
  var gulpif = require('gulp-if');
  var gutil = require('gulp-util');
  var watch = require('gulp-watch');
  var webpack = require('webpack');

  // js
  var jscs = require('gulp-jscs');
  var jshint = require('gulp-jshint');
  var stylish = require('jshint-stylish');

  // html
  var htmlhint = require('gulp-htmlhint');

  // json
  var jsonlint = require('gulp-jsonlint');

  // scss
  var sourcemaps = require('gulp-sourcemaps');
  var sass = require('gulp-sass');

  // Files will be output here
  var staticBuildDestination = 'orchestra/static/dist/';

  var files = {
    scss: [
      'orchestra/static/orchestra/timing/timer/timer.scss',
      'orchestra/static/orchestra/common/css/orchestra.scss',
    ],
    all_scss: [],
    jslint: [
      './gulpfile.js' // Lint ourselves!
    ],
    jsonlint: [
      '**/*.json',
      '!node_modules/**',
    ],
    htmllint: [],
  };

  var installedApps = [
    'orchestra',
  ];

  for (var i = 0; i < installedApps.length; i++) {
    var appName = installedApps[i];
    files.all_scss.push(appName + '/static/**/*.scss');

    // jslint
    files.jslint.push(appName + '/static/**/*.js');
    files.jslint.push('!' + appName + '/static/**/common/js/lib/**');
    files.jslint.push('!' + appName + '/static/dist/**/*.js');
    files.jslint.push('!' + appName + '/static/**/dist2/**');
    files.jslint.push('!' + appName + '/static/**/*.min.js');
    files.jslint.push('!' + appName + '/static/**/*.es6.js');

    // htmllint
    files.htmllint.push(appName + '/static/**/*.html');
  }

  gulp.task('scss', function() {
    return gulp.src(files.scss, {
        base: './'
      })
      .pipe(gulpif(!argv.production, sourcemaps.init()))
      .pipe(sass())
      .pipe(gulpif(!argv.production, sourcemaps.write()))
      .pipe(rename(function(path) {
        // move to a css dir if it is in a scss dir
        var dirname = path.dirname;
        dirname = dirname.replace('/scss', '/css');
        var chopPath = '/static/';
        dirname = dirname.substring(dirname.indexOf(chopPath) + chopPath.length);
        path.dirname = dirname;
        return path;
      }))
      .pipe(gulp.dest(staticBuildDestination));
  });

  gulp.task('jslint', function() {
    return gulp.src(files.jslint)
      .pipe(cache('jslint'))
      .pipe(jshint())
      .pipe(jshint.reporter(stylish))
      .pipe(gulpif(argv.production, jshint.reporter('fail')))
      .pipe(jscs())
      .pipe(jscs.reporter());
  });

  gulp.task('jsonlint', function() {
    return gulp.src(files.jsonlint)
      .pipe(cache('jsonlint'))
      .pipe(jsonlint())
      .pipe(jsonlint.reporter())
      .pipe(gulpif(argv.production, jsonlint.failOnError()));
  });

  gulp.task('htmllint', function() {
    return gulp.src(files.htmllint)
      .pipe(cache('htmllint'))
      .pipe(htmlhint('.htmlhintrc'))
      .pipe(htmlhint.reporter())
      .pipe(gulpif(argv.production, htmlhint.failReporter()));
  });

  // TODO(joshblum): add css and scss linting
  gulp.task('lint', gulp.parallel('jslint', 'jsonlint', 'htmllint'));

  gulp.task('watch', function() {
    var all_lint_files = [].concat.apply([], [files.jslint, files.jsonlint]);
    gulp.watch(all_lint_files, gulp.series('lint'));
    gulp.watch(files.all_scss, gulp.series('scss'));
    gulp.watch(all_lint_files, gulp.series('webpack'));
  });

  gulp.task('webpack', function(callback) {
    webpack(require('./webpack.config.js'), function(err, stats) {
      if (err) {
        throw new gutil.PluginError('webpack', err);
      }
      gutil.log('[webpack]', stats.toString());
      callback();
    });
  });

  gulp.task('build', gulp.parallel('lint', 'scss'));
  gulp.task('default', gulp.series('build', 'watch'));
})();
