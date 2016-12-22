import dragula from 'dragula'
import 'dragula/dist/dragula.min.css'

import template from './checklist.html'
import './checklist.scss'

export default function orchestraChecklist ($http, $timeout, $compile, orchestraService) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      'data': '=',
      'author': '@?',
      'imagePrefix': '@?'
    },
    link: function (scope, el, attr) {
      var sampleItem = {
        'title': 'Update the hero image ' +
          '(This is a sample item! Click on the text to edit or ' +
          'click to the right to expand.)',
        'comments': [{
          'author': 'jane',
          'timestamp': new Date(new Date() - 3 * 60 * 60 * 1000),
          'text': "The hero image you've chosen doesn't fit " +
            'well with the color scheme. Try something ' +
            'less washed out?'
        }, {
          'author': 'john',
          'timestamp': new Date(new Date() - 2 * 60 * 60 * 1000),
          'text': 'Sounds good! I swapped it out, what do ' +
            'you think? '
        }, {
          'author': '',
          'text': 'This is a sample checklist comment. ' +
            'You can add a new comment for each new ' +
            'round of iteration on your work!'
        }],
        'checked': false,
        'expanded': false,
        'readonly': true,
        'index': 0,
        'order': 0
      }

      // Initialize checklist data for a fresh task
      scope.data = scope.data || {}
      scope.data.items = scope.data.items || [sampleItem]
      scope.data.deletedItems = scope.data.deletedItems || []
      scope.hideCompleted = false

      // Prepare data for submit
      orchestraService.signals.registerSignal('submit.before', function () {
        scope.data.items.forEach(function (item) {
          // Add author and date information to the latest comment. Then,
          // create a new comment space for the next worker.
          if (item.comments[item.comments.length - 1].text) {
            item.comments[item.comments.length - 1].author = scope.author
            item.comments[item.comments.length - 1].timestamp = Date.now()
            item.comments.push({
              'author': '',
              'text': ''
            })
          }
        })
      })

      orchestraService.signals.registerSignal('submit.error', function () {
        scope.data.items.forEach(function (item) {
          // Revert comment changes from submit.before handler
          if (item.comments[item.comments.length - 1].text) {
            item.comments.pop()
            item.comments[item.comments.length - 1].author = ''
            item.comments[item.comments.length - 1].timestamp = undefined
          }
        })
      })

      // Setup drag to reorder
      scope.preventAction = false
      var checklistContainer = el.find('ul.checklist')
      var drake = dragula([checklistContainer.get(0)], {
        moves: function (el, container, handle) {
          // Item title input only when readonly (so user can select text within input)
          // Item title container outside of input
          return handle.className.indexOf('checklist-item') >= 0 || (handle.className.indexOf('item-title-input') >= 0 && handle.className.indexOf('readonly') >= 0) || (handle.className.indexOf('item-title') >= 0 && handle.className.indexOf('item-title-input') < 0)
        },
        invalid: function (el, target) {
          return scope.preventAction
        }
      })

      // Prevent another drag from occuring until the current drag is
      // completed and the new order is set.
      drake.on('drag', function () {
        scope.preventAction = true
        scope.$apply()
      })
      drake.on('dragend', function () {
        setOrder()
        scope.preventAction = false
        scope.$apply()
      })

      // Determines and saves the order changed by drag event
      var setOrder = function () {
        var items = el.get(0).querySelectorAll('.checklist-item')

        for (var i = 0; i < items.length; i++) {
          var item = items[i]
          getItemByKey(item.getAttribute('data-key')).order = i
        }
      }

      // Retrieves checklist item based on angular object key
      var getItemByKey = function (key) {
        var item
        for (var i = scope.data.items.length - 1; i >= 0; i--) {
          item = scope.data.items[i]
          if (item.$$hashKey === key) {
            return item
          }
        }
      }

      // Add new checklist item
      scope.addItem = function () {
        scope.data.items.push({
          'title': '',
          'comments': [{
            'author': scope.author,
            'text': ''
          }],
          'checked': false,
          'expanded': false,
          'readonly': true,
          'order': scope.data.items.length
        })
      }

      // Remove checklist item
      scope.removeItem = function (item, confirmNeeded) {
        var index = scope.data.items.indexOf(item)
        if (!confirmNeeded || window.confirm('Are you sure you want to delete this item?')) {
          scope.preventAction = true
          scope.data.items.splice(index, 1)
          scope.data.deletedItems.push(item)

          // Reset order after $digest block (once item has been removed)
          $timeout(function () {
            setOrder()
            scope.preventAction = false
          }, 0, false)
        }
      }

      // Allow checklist title to be edited
      scope.editItem = function (item, $event) {
        if (item.readonly) {
          // Item will become editable
          if ($event) {
            // Set focus on input
            $event.target.focus()
          }
          scope.data.items.forEach(function (scopeItem) {
            scopeItem.readonly = true
          })
        }
        item.readonly = !item.readonly
      }

      // Expand checklist item to show comments
      scope.expandItem = function (item) {
        item.expanded = !item.expanded
        scope.data.items.forEach(function (scopeItem) {
          scopeItem.readonly = true
        })
      }

      // Return localized comment timestamp
      scope.getCommentTimestamp = function (comment) {
        return new Date(comment.timestamp).toLocaleString()
      }
    }
  }
}
