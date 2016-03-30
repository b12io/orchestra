var gulp = require('gulp');
var cache = require('gulp-cached');
var jscs = require('gulp-jscs');
var jshint = require('gulp-jshint');
var ngAnnotate = require('gulp-ng-annotate');
var print = require('gulp-print');
var rename = require('gulp-rename');
var sass = require('gulp-sass');
var sourcemaps = require('gulp-sourcemaps');
var stylish = require('jshint-stylish');
var uglify = require('gulp-uglify');
var watch = require('gulp-watch');

var buildDestination = 'orchestra/static/dist';

var files = {
  scss: [
    'orchestra/static/orchestra/common/components/checklist/css/checklist.scss',
    'orchestra/static/orchestra/common/components/iframe/css/iframe.scss',
    'orchestra/static/orchestra/common/components/quill/css/quill.scss',
    'orchestra/static/orchestra/common/css/orchestra.scss',
    'orchestra/static/orchestra/common/css/registration.scss',
    'orchestra/static/orchestra/dashboard/css/dashboard.scss',
    'orchestra/static/orchestra/task/css/task.scss',
  ],
  all_scss: [],
  scripts: [
    '!' + buildDestination + '/**',
    '!**/common/js/lib/**'
  ]
};

var installedApps = [
  'orchestra',
];

for (var i = 0; i < installedApps.length; i++) {
  var appName = installedApps[i];
  files.scripts.push(appName + '/static/**/*.js');
  files.scripts.push('!' + appName + '/static/**/*.min.js');
  files.all_scss.push(appName + '/static/**/*.scss');
}


gulp.task('default', ['build', 'watch']);
gulp.task('build', ['scss', 'lint', 'scripts']);

gulp.task('scss', function() {
  return gulp.src(files.scss)
    .pipe(sass())
    .pipe(gulp.dest(buildDestination));
});

gulp.task('lint', function() {
  return gulp.src(files.scripts)
    .pipe(cache('lint'))
    .pipe(jshint())
    .pipe(jshint.reporter(stylish))
    .pipe(jshint.reporter('fail'))
    .pipe(jscs())
    .pipe(jscs.reporter())
});

gulp.task('scripts', function() {
  return gulp.src(files.scripts)
    .pipe(cache('scripts'))
    .pipe(sourcemaps.init())
    .pipe(ngAnnotate())
    .pipe(uglify({mangle: false}))
    .pipe(rename({
      suffix: '.min'
    }))
    .pipe(sourcemaps.write())
    .pipe(gulp.dest(buildDestination));
});

gulp.task('watch', function() {
  gulp.watch(files.all_scss, ['scss']);
  gulp.watch(files.scripts, ['scripts']);
});
