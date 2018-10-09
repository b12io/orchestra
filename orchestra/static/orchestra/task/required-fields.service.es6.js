export default function requiredFields ($rootScope, orchestraService) {
  /**
   * Service to keep track of all required fields in a task view and
   * validate them on submit.
   */
  'ngAnnotate'
  var requiredFields = {
    validators: {
      'input-checkbox': [
        function (elems) {
          return elems[0].checked
        }
      ],
      'input-text': [
        function (elems) {
          return elems[0].value && elems[0].value.length > 0
        }
      ],
      'input-radio': [
        function (elems) {
          return Array.from(elems).some(function (elem) { return elem.checked })
        }
      ]
    },
    setup: function (data) {
      /**
       * Sets up the base data on which to validate fields.
       */
      this.fields = {}
      this.invalid = []
      this.data = data
    },
    require: function (fieldType, field) {
      /**
       * Sets a field as required. Fields are HTML elements to be
       * checked by one or more validators according to their field
       * type.
       */
      if (this.fields[fieldType] === undefined) {
        this.fields[fieldType] = [field]
      } else {
        this.fields[fieldType].push(field)
      }
    },
    validate: function () {
      /**
       * Validates required fields according to their registered
       * validators.
       */
      var requiredFields = this
      requiredFields.invalid = []

      /* jshint -W083 */
      // Hide error for creating a function in a loop
      for (var fieldType in requiredFields.fields) {
        var validators = requiredFields.validators[fieldType]
        if (!validators) {
          console.error('Validators not found for field type:' + fieldType)
          continue
        }
        var fields = requiredFields.fields[fieldType]
        fields.forEach(function (field) {
          var success = true
          validators.forEach(function (validator) {
            success = success && validator(field)
          })
          if (!success) {
            requiredFields.invalid.push(field)
          }
        })
      }
      $rootScope.$broadcast('orchestra:task:validatedFields')
      return requiredFields.invalid.length === 0
    },
    registerValidator: function (fieldType, validator) {
      /**
       * Register a validator function to the given field type.
       */
      var requiredFields = this
      if (requiredFields.validators[fieldType] === undefined) {
        requiredFields.validators[fieldType].push(validator)
      } else {
        requiredFields.validators[fieldType] = [validator]
      }
    }
  }

  orchestraService.signals.registerSignal(
    'submit.before', function () {
      if (!requiredFields.validate()) {
        window.alert('One or more required fields have not been filled out.')
        return false
      }
    })

  return requiredFields
}
