// dependencies
define([], function() {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        this.app        = app;
        this.options    = options;
    },
            
    // render
    draw : function(process_id, nvd3_model, chart, request_dictionary, callback)
    {
        // request data
        var self = this;
        this.app.datasets.request(request_dictionary, function() {
            nv.addGraph(function() {
                // x axis
                self._axis(nvd3_model.xAxis, chart.settings.get('x_axis_type'), chart.settings.get('x_axis_tick'));
                
                // x axis label
                nvd3_model.xAxis.axisLabel(chart.settings.get('x_axis_label'));
                
                // y axis
                self._axis(nvd3_model.yAxis, chart.settings.get('y_axis_type'), chart.settings.get('y_axis_tick'));
                
                // y axis label
                nvd3_model.yAxis.axisLabel(chart.settings.get('y_axis_label'))
                                .axisLabelDistance(30);
                
                // controls
                nvd3_model.options({showControls: false});
                
                // legend
                if (nvd3_model.showLegend) {
                    var legend_visible = true;
                    if (chart.settings.get('show_legend') == 'false') {
                        legend_visible = false;
                    }
                    nvd3_model.showLegend(legend_visible);
                }
                
                // custom callback
                if (callback) {
                    callback(nvd3_model);
                }
                
                // parse data to canvas
                self.options.canvas[0].datum(request_dictionary.groups)
                                      .call(nvd3_model);
     
                // refresh on window resize
                nv.utils.windowResize(nvd3_model.update);
                
                // set chart state
                chart.state('ok', 'Chart has been drawn.');
                
                // unregister process
                chart.deferred.done(process_id);
            });
        });
    },
    
    // make axis
    _axis: function(axis, type, tick) {
        switch (type) {
            case 'hide':
                axis.tickFormat(function() { return '' });
                break;
            case 'auto':
                break;
            default:
                axis.tickFormat(d3.format(tick + type));
        }
    }
});

});