export default function crosshair (visUtils, axis) {
  /**
   * Service to overlay the project management visualization with a crosshair
   * aligned to the time axis.
   */
  'ngAnnotate'
  var _svg
  var _line

  return {
    setup: function () {
      _svg = visUtils.parentContainer.append('svg')
        .style({
          'opacity': 0,
          'position': 'absolute',
          'top': 0,
          // Bring to front of visualization
          'z-index': 1
        })
      _line = _svg.append('line')
        .attr({
          'class': 'crosshair',
          'stroke': 'rgb(0, 121, 191)',
          'x1': 0,
          'x2': 0,
          'y1': 0
        })
    },
    draw: function () {
      /**
       * Draws/updates crosshair container within visualization.
       */
      _svg.attr({
        'height': visUtils.getSvgHeight(),
        'width': 1
      })
      _line.attr({
        'y2': function () {
          return visUtils.getSvgHeight()
        }
      })
    },
    show: function () {
      /**
       * Shows the crosshair.
       */
      this.draw()
      // TODO(jrbotros): crosshair doesn't show for all revert flags on Safari.
      _svg.style('opacity', 1)
    },
    hide: function () {
      /**
       * Hides the crosshair.
       */
      _svg.style('opacity', 0)
    },
    move: function (datetime) {
      /**
       * Moves the crosshair to the specified datetime.
       */
      _svg.style('left', (visUtils.params.marginLeft + axis.timeScale(datetime)) + 'px')
    }
  }
}
