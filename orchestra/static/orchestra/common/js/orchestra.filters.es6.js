import {
  isObject
} from 'lodash'

export function capitalize () {
  return function (input, format) {
    if (!input) {
      return input
    }
    // Capitalize the first letter of an input
    return input.charAt(0).toUpperCase() + input.slice(1)
  }
}

export function toArray () {
  // Modified from github.com/petebacondarwin/angular-toArrayFilter
  return function (obj, addKey) {
    if (!isObject(obj)) {
      return obj
    }
    if (addKey === false) {
      return Object.keys(obj).map(function (key) {
        return obj[key]
      })
    } else {
      return Object.keys(obj).map(function (key) {
        var value = obj[key]
        if (isObject(value)) {
          return Object.defineProperty(value, '$key', {
            enumerable: false, value: key
          })
        } else {
          return {
            $key: key, $value: value
          }
        }
      })
    }
  }
}
