angular.module('angular-capitalize-filter', [])
  .filter('capitalize', function() {
    return function (input, format) {
      if (!input) {
        return input;
      }
      // Capitalize the first letter of an input
      return input.charAt(0).toUpperCase() + input.slice(1);
    };
  });
