import template from './quill.html'

// TODO(jrbotros): update to v1.0.0
import Quill from 'quill'
import 'quill/dist/quill.base.css'
import 'quill/dist/quill.snow.css'
import './quill.scss'

export default function orchestraQuill ($http, $timeout) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      'data': '=',
      'imagePrefix': '=?',
      'readonly': '=',
      'uploadLimitMb': '=?'
    },
    link: function (scope, el, attr) {
        // Suggested limit for image upload size is 5 MB.
      scope.uploadLimitMb = scope.uploadLimitMb || 5

        // Default image prefix is an empty string.
      scope.imagePrefix = scope.imagePrefix || ''

        // Containers within directive template for Quill editor
      var editorContainer = el.find('.orchestra-quill-editor').get(0)
      var toolbarContainer = el.find('.orchestra-quill-toolbar').get(0)

      scope.editor = new Quill(editorContainer, {
        modules: {
          'toolbar': {
            container: toolbarContainer
          },
            // Image tooltip removed in favor of file selector dialog
          'link-tooltip': true
        },
        theme: 'snow'
      })

        // Set up two-way link between quill and parent scope attribute passed
        // in by directive caller
      scope.$watch('data', function (now, before) {
        if (scope.data && scope.data !== scope.editor.getHTML()) {
          scope.editor.setHTML(scope.data)
        }
      })

        // Editor set to read-only upon initialization.
      if (scope.readonly) {
        scope.editor.editor.disable()
        toolbarContainer.remove()
        return
      }

      scope.editor.on('text-change', function () {
          // Set the focus outside the $digest block.
          // Taken from https://docs.angularjs.org/error/$rootScope/inprog?p0=$digest.
        $timeout(function () {
          scope.data = scope.editor.getHTML()
          scope.$apply()
        }, 0, false)
      })

        // Upload image via the toolbar button
      scope.fileSelector = document.createElement('input')
      scope.fileSelector.setAttribute('type', 'file')
      scope.fileSelector.setAttribute('accept', 'image/*')
      var imageSelector = el.find('.orchestra-quill-toolbar .ql-image').get(0)
      scope.fileSelector.onchange = function (e) {
          // Focus the editor so we can get the current selection.
        scope.editor.focus()
        var files = scope.fileSelector.files
        for (var i = files.length - 1; i >= 0; i--) {
          if (files[i] !== null) {
            uploadImage(files[i], scope.editor.getSelection())
          }
        }
      }
      imageSelector.onclick = function () {
        scope.fileSelector.click()
        return false
      }

        // TODO(jrbotros): move paste/drop functionality into a quilljs fork

        // Upload image by pasting in copied image data
      editorContainer.addEventListener('paste', pasteImage, true)

      function pasteImage (e) {
        if (e.clipboardData && e.clipboardData.items) {
          var copiedData = e.clipboardData.items[0]
          var imageFile = copiedData.getAsFile()
          uploadImage(imageFile, scope.editor.getSelection(), e)
        }
      }

        // Upload image by drag and drop
      editorContainer.addEventListener('drop', dropImage, true)

      function dropImage (e) {
        var files = e.dataTransfer.files
        for (var i = files.length - 1; i >= 0; i--) {
          var file = files[i]
          var dropOffset = getDropIndexOffset(e)
          uploadImage(file, {
            'start': dropOffset,
            'end': dropOffset
          }, e)
        }
      }

      function getDropIndexOffset (dropEvent) {
          /**
           * Given a drop event, calculate the index offset within the
           * Quill editor by:
           *   - determining the character offset of the drop within the inner node
           *   - finding all editor leaf nodes (reimplements some Quill functionality)
           *   - calculating the index offset from the leaf node lengths and inner drop node offset
           * We plan to push this functionality into Quill in the future.
           */
        function getDropCharOffset (x, y) {
            // Helper function for getting the x-y character offset of a drop
            // event in a contenteditable field.
            // Modified from http://stackoverflow.com/a/10659990.
          var range
            // Standards-based way; implemented only in Firefox
          if (document.caretPositionFromPoint) {
            var pos = document.caretPositionFromPoint(x, y)
            return {
              'offset': pos.offset,
              'node': pos.offsetNode
            }
          } else if (document.caretRangeFromPoint) {
              // Webkit
            range = document.caretRangeFromPoint(x, y)
            return {
              'offset': range.startOffset,
              'node': range.startContainer
            }
          } else if (document.body.createTextRange) {
              // IE doesn't natively support retrieving the character offset, so
              // insert image at end of text
              // TODO(jrbotros): rewrite with https://github.com/timdown/rangy
            return
          }
        }

        function getAllChildNodes (parent) {
            // Returns in-order list of all child nodes of `parent`
          var bfsStack = [parent]
          var nodes = []
          while (bfsStack.length) {
            var currentNode = bfsStack.pop()
            if (currentNode.childNodes) {
                // Concat with copy of child NodeList; can't use pop operation
                // on original
              bfsStack = bfsStack.concat(Array.prototype.slice.call(currentNode.childNodes))
            }
            nodes.push(currentNode)
          }
          return nodes.reverse()
        }

          // http://stackoverflow.com/a/22289650
        function getLeafNodes (parent) {
            // Returns in-order list of all Quill leaf nodes of `parent`
          var textNodeType = 3
          var nodes = getAllChildNodes(parent)
          var leafNodes = nodes.filter(function (elem) {
            return elem.nodeType === textNodeType || !elem.firstChild
          })
          return leafNodes
        }

        var caretPosition = getDropCharOffset(dropEvent.clientX, dropEvent.clientY)
        if (!caretPosition) {
          return scope.editor.getLength()
        }
        var leaves = getLeafNodes(editorContainer.getElementsByClassName('ql-editor')[0])
        var opIndex = leaves.indexOf(caretPosition.node)
        var contents = scope.editor.getContents()
        contents.ops = contents.ops.slice(0, opIndex)
        return contents.length() + caretPosition.offset
      }

        // Post image data to an API endpoint that returns an image URL, then
        // adding it to the editor (replacing the given character range)
      function uploadImage (file, range, e) {
        var uploadAPIEndpoint = '/orchestra/api/interface/upload_image/'
        var supportedTypes = ['image/jpeg', 'image/png', 'image/gif']

        if (supportedTypes.indexOf(file.type) === -1) {
          window.alert('Files type ' + file.type + ' not supported.')
          return
        } else if (e) {
            // Cancel default browser action only if file is actually an image
          e.preventDefault()
        }

          // If nothing is selected in the editor, append the image to its end
        if (range === null) {
          var endIndex = scope.editor.getLength()
          range = {
            'start': endIndex,
            'end': endIndex
          }
        }

        var reader = new window.FileReader()
        reader.onload = function (e) {
          var rawData = e.target.result
            // Remove prepended image type from data string
          var imageData = rawData.substring(rawData.indexOf(',') + 1, rawData.length)

            // Calculate data size of b64-encoded string
          var imageSize = imageData.length * 3 / 4

          if (imageSize > scope.uploadLimitMb * Math.pow(10, 6)) {
            window.alert('Files larger than ' + scope.uploadLimitMb + 'MB cannot be uploaded')
            return
          }
            // Post image data to API; response should contain the uploaded image url
          $http.post(uploadAPIEndpoint, {
            'image_data': imageData,
            'image_type': file.type,
            'prefix': scope.imagePrefix
          })
              .then(function (response, status, headers, config) {
                // Replace selected range with new image
                scope.editor.deleteText(range)
                scope.editor.insertEmbed(range.start, 'image', response.data.url, 'user')
              })
        }
        reader.readAsDataURL(file)
      }
    }
  }
}
