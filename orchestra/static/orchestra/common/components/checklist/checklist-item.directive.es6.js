import template from './checklist-item.html'

export default function orchestraChecklistItem ($http, $timeout, $compile, orchestraService) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    link: function (scope, el, attr) {
      // Dynamically autosize a text input to fit its contents.
      // Modified from https://github.com/yuanqing/autosize-input (MIT license).
      scope.autosizeInput = function (elem, ghost, minWidth, str) {
        // Compile and cache the needed regular expressions.
        var SPACE = /\s/g
        var LESS_THAN = />/g
        var MORE_THAN = /</g

        // We need to swap out these characters with their character-entity
        // equivalents because we're assigning the resulting string to
        // `ghost.innerHTML`.
        function escape (str) {
          return str.replace(SPACE, '&nbsp;')
            .replace(LESS_THAN, '&lt;')
            .replace(MORE_THAN, '&gt;')
        }

        str = str || elem.value || ''

        // Apply the `font-size` and `font-family` styles of `elem` on the
        // `ghost` element.
        var elemStyle = window.getComputedStyle(elem)
        var elemCssText = 'font-family:' + elemStyle.fontFamily +
          ';font-size:' + elemStyle.fontSize

        ghost.style.cssText += elemCssText
        ghost.innerHTML = escape(str)
        var width = window.getComputedStyle(ghost).width
        if (width === '0px') {
          width = minWidth
        }
        elem.style.width = width
        return width
      }

      // Helper function that:
      // 1. Copies the `font-family` and `font-size` of our `elem` onto `ghost`
      // 2. Sets the contents of `ghost` to the specified `str`
      // 3. Copies the width of `ghost` onto our `elem`
      scope.setupAutosizer = function (elem) {
        // Create the `ghost` element, with inline styles to hide it and ensure that
        // the text is all on a single line.
        var ghost = document.createElement('div')
        ghost.className = 'ghost'
        ghost.style.cssText = 'box-sizing:content-box;display:inline-block;height:0;overflow:hidden;position:absolute;top:0;visibility:hidden;white-space:nowrap;'
        document.body.appendChild(ghost)

        // Force `content-box` on the `elem`.
        elem.style.boxSizing = 'content-box'

        var minWidth = scope.autosizeInput(elem, ghost, 0, elem.getAttribute('placeholder'))

        // Autosize input on value change
        elem.addEventListener('input', function () {
          scope.autosizeInput(elem, ghost, minWidth)
        })

        // Autosize input when checklist item first added to the DOM
        $timeout(function () {
          scope.autosizeInput(elem, ghost, minWidth)
        }, 0)
      }

      scope.setupAutosizer(el.find('.item-title input').get(0))
    }
  }
}
