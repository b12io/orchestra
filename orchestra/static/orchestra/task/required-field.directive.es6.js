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
      var fieldElements = elem.find('input')
      var firstField = fieldElements[0]
      var fieldType = firstField.getAttribute('type')
      var errorClass = elem.attr('data-error-class')
      if (!errorClass) {
        errorClass = fieldType + '-error'
      }
      if (firstField &&
          fieldType !== 'radio' &&
          fieldType !== 'checkbox' &&
          fieldType !== 'text') {
        console.error('Unsupported required field type.')
        return
      }
      var fieldsToValidate = (fieldType === 'radio')
        ? fieldElements
        : firstField
      requiredFields.require('input-' + fieldType, fieldsToValidate)
      var toggleError = function () {
        if (requiredFields.invalid.indexOf(firstField) >= 0) {
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
