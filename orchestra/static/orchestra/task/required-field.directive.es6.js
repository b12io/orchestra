/**
 * Provides a directive to wrap required fields in task views.
 *   - The wrapped HTML should contain an input element bound with
 *     ngModel.
 *   - Optionally provide a class to add to the directive wrapper on
 *     error with `data-error-class="error-class"` on the directive
 *     element; otherwise, a default is provided for the input type.
 */
export default function orchestraRequiredField ($compile, requiredFields) {
  'ngAnnotate'
  return {
    restrict: 'EA',
    link: function (scope, elem, attrs) {
      var field = elem.find('input')[0]
      var errorClass = elem.attr('data-error-class')
      if (!errorClass) {
        errorClass = field.getAttribute('type') + '-error'
      }
      if (field &&
          field.getAttribute('type') !== 'checkbox' &&
          field.getAttribute('type') !== 'text') {
        console.error('Unsupported required field type.')
        return
      }
      requiredFields.require('input-' + field.getAttribute('type'), field)
      var toggleError = function () {
        if (requiredFields.invalid.indexOf(field) >= 0) {
          elem.addClass('required-field-error ' + errorClass)
        } else {
          elem.removeClass('required-field-error ' + errorClass)
        }
      }
      toggleError()
      scope.$on('orchestra:task:validatedFields', toggleError)
    }
  }
}
