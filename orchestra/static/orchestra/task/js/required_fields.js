(function() {
  'use strict';

  var serviceModule =  angular.module('orchestra.task.services');

  /**
   * Service to keep track of all required fields in a task view and
   * validate them on submit.
   */
  serviceModule.factory('requiredFields', function($rootScope, orchestraService) {
    var requiredFields = {
      fields: [],
      invalid: [],
      setup: function(data) {
        /**
         * Sets up the base data on which to validate fields.
         */
        this.data = data;
      },
      require: function(fields) {
        /**
         * Sets a field as required. Fields are specified by
         * dot-delimited key strings (e.g., `key0.key1.key2`).
         */
        this.fields = this.fields.concat(fields)
      },
      validate: function() {
        /**
         * Validates required fields. For the required field
         * `key0.key1.key2` to be valid, `this.data[key0][key1][key2]`
         * must exist and not be falsy.
         */
        var requiredFields = this;
        requiredFields.invalid = [];
        requiredFields.fields.forEach(function(field) {
          // For each field, check that each successive key exists and
          // is not falsy.
          var obj = requiredFields.data;
          var keys = field.split('.');
          for (var i in keys) {
            var key = keys[i];
            obj = obj[key];
            if (!obj) {
              requiredFields.invalid.push(field)
              break;
            }
          }
        })
        $rootScope.$broadcast('orchestra:task:validatedFields');
        return requiredFields.invalid.length === 0;
      }
    };

    orchestraService.signals.registerSignal(
      'submit.before', function() {
        if (!requiredFields.validate()) {
          alert('One or more required fields have not been filled out.')
          return false;
        };
      });

    return requiredFields;
  });

  /**
   * Provides a directive to wrap required fields in task views.
   *   - The wrapped HTML should contain an input element bound with
   *     ngModel.
   *   - Optionally provide a class to add to the directive wrapper on
   *     error with `data-error-class="error-class"` on the directive
   *     element; otherwise, a default is provided for the input type.
   */
  angular.module('orchestra.task.directives')
    .directive('orchestraRequiredField', function($compile, requiredFields) {
      return {
        restrict: 'EA',
        link: function(scope, elem, attrs) {
          var errorClass = elem.attr('data-error-class');
          if (!errorClass) {
            var type = elem.find('input').attr('type');
            errorClass = type + '-error';
          }
          var field = elem.find('input').attr('ng-model');
          requiredFields.require([field]);
          var toggleError = function() {
            if (requiredFields.invalid.indexOf(field) >= 0) {
              elem.addClass('required-field-error ' + errorClass);
              scope.$watch(field, function(oldVal, newVal) {
                if (oldVal != newVal) {
                  elem.removeClass('required-field-error ' + errorClass);
                }
              })
            }
            else {
              elem.removeClass('required-field-error ' + errorClass);
            }
          }
          toggleError();
          scope.$on('orchestra:task:validatedFields', toggleError);
        }
      };
    });

})()
