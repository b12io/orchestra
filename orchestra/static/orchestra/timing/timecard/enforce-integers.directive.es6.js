export default function enforceIntegers () {
  // Non-digit chars are accepted in number inputs in some browsers (e.g., Safari)
  // Modified from stackoverflow.com/a/14425022
  'ngAnnotate'
  return {
    scope: {
      max: '=?',
      min: '=?'
    },
    require: 'ngModel',
    link: function (scope, element, attrs, modelCtrl) {
      modelCtrl.$parsers.unshift(function (inputValue) {
        if (inputValue === undefined || inputValue === null) {
          modelCtrl.$setViewValue(0)
          modelCtrl.$render()
          return
        }

        var transformedInput = String(inputValue).replace(/[^\d]/g, '')

          // Remove leading 0 if present
        if (transformedInput.length && transformedInput[0] === '0') {
          transformedInput = transformedInput.substring(1)
        }

          // Convert to integer
        if (transformedInput.length) {
          transformedInput = parseInt(transformedInput, 10)
          transformedInput = Math.min(transformedInput, scope.max)
          transformedInput = Math.max(transformedInput, scope.min)
        } else {
          transformedInput = 0
        }

        if (transformedInput !== inputValue) {
          modelCtrl.$setViewValue(transformedInput)
          modelCtrl.$render()
        }

        return transformedInput
      })
    }
  }
}
