/* global angular */

export function capitalize () {
  return function (input, format) {
    if (!input) {
      return input
    }
    // Capitalize the first letter of an input
    return input.charAt(0).toUpperCase() + input.slice(1)
  }
}

  // Modified from github.com/petebacondarwin/angular-toArrayFilter
export function toArray () {
  return function (obj, addKey) {
    if (!angular.isObject(obj)) return obj
    if (addKey === false) {
      return Object.keys(obj).map(function (key) {
        return obj[key]
      })
    } else {
      return Object.keys(obj).map(function (key) {
        var value = obj[key]
        return angular.isObject(value)
          ? Object.defineProperty(value, '$key', { enumerable: false, value: key })
          : { $key: key, $value: value }
      })
    }
  }
}
