// dependencies
define(['plugin/charts/tools', 'utils/utils', 'plugin/charts/others/heatmap/heatmap-parameters'], function(Tools, Utils, HeatmapParameters) {

// widget
return Backbone.View.extend({
    
    // options
    optionsDefault: {
        margin: {
            top                 : 40,
            right               : 70,
            bottom              : 70,
            left                : 70
        },
        style: {
            'font-weight'       : 'normal',
            'font-family'       : 'Verdana',
            'font-size'         : 12
        },
        legend: {
            width               : 15,
            size                : 0.9,
            style : {
                'font-weight'   : 'normal',
                'font-family'   : 'Verdana',
                'font-size'     : 11
            },
            limit               : 7
        },
        background_color        : '#FFFFFF',
        debug_color             : '#FFFFFF'
    },
    
    // initialize
    initialize: function(app, options) {
        // collect parameters
        this.app            = app;
        this.chart          = options.chart;
        this.canvas_id      = options.canvas_id;
        this.group          = options.groups[0];
        this.data           = options.groups[0].values;
        this.options        = Utils.merge (this.optionsDefault, options);
        
        // get color set
        this.color_set = HeatmapParameters.colorSets[this.chart.settings.get('color_set')];
        
        // categories
        this.categories = Tools.makeUniqueCategories([this.group]);
        
        // domains/scales
        this.xScale = d3.scale.linear().domain([0, this.categories.array.x.length]);
        this.yScale = d3.scale.linear().domain([0, this.categories.array.y.length]);
        
        // color scale
        this.zMin = d3.min(this.data, function(d) { return d.z; });
        this.zMax = d3.max(this.data, function(d) { return d.z; });
        this.zScale = d3.scale.quantize().domain([this.zMin, this.zMax]).range(this.color_set);

        // create axis
        this.xAxis = d3.svg.axis().scale(this.xScale).orient('bottom');
        this.yAxis = d3.svg.axis().scale(this.yScale).orient('left');
        
        // make categories
        this._makeTickFormat('x');
        this._makeTickFormat('y');
        
        // add tooltip
        this.tooltip = d3.select('.charts-viewport-container').append('div')
            .attr('class', 'charts-tooltip')
            .style(this.options.style)
            .style('opacity', 0);
        
        // refresh on window resize
        var self = this;
        $(window).on('resize', function () {
            self.redraw();
        });
        
        // draw
        this.redraw();
                    
        // add zoom
        Tools.addZoom({
            xAxis       : this.xAxis,
            yAxis       : this.yAxis,
            redraw      : function() { self.redraw(); },
            svg         : d3.select('#' + this.canvas_id)
        });
    },
        
    // redraw
    redraw: function() {
        // get parameters
        var chart       = this.chart;
        var data        = this.data;
        var self        = this;
        this.data       = data;
        
        // get/reset container
        var container = $('#' + this.canvas_id);
        container.empty();
        
        // get domain
        var xDomain = this.xScale.domain();
        var yDomain = this.yScale.domain();
        
        // set ticks
        var xTickStart = Math.ceil(xDomain[0]);
        var xTickEnd   = Math.floor(xDomain[1]);
        var yTickStart = Math.ceil(yDomain[0]);
        var yTickEnd   = Math.floor(yDomain[1]);
        this.xAxis.tickValues(d3.range(xTickStart, xTickEnd, 1));
        this.yAxis.tickValues(d3.range(yTickStart, yTickEnd, 1));
        
        // get margins
        var margin = this.options.margin;
        
        // configure dimensions
        this.height = parseInt(container.height()) - margin.top - margin.bottom;
        this.width  = parseInt(container.width()) - margin.left - margin.right;
        
        // set range
        this.xScale.range([0, this.width]);
        this.yScale.range([this.height, 0]);

        // get box properties
        this.rowCount = yDomain[1] - yDomain[0];
        this.colCount = xDomain[1] - xDomain[0];
        this.boxWidth = Math.max(1, Math.floor(this.width / this.colCount));
        this.boxHeight = Math.max(1, Math.floor(this.height / this.rowCount));
        
        // create group
        var svg = this.svg = d3.select('#' + this.canvas_id)
            .append('g')
                .attr('class', 'heatmap')
                .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
        
        // build elements
        this._buildBoxes();
        this._buildX();
        this._buildY();
        
        // show legend only if requested
        if (this.chart.settings.get('show_legend') == 'true') {
            this._buildLegend();
        }
    },
    
    // y axis
    _buildBoxes: function() {
        // link this
        var self = this;
        
        // collect parameters
        var height      = this.height;
        var width       = this.width;
        var margin      = this.options.margin;
        var svg         = this.svg;
        var boxWidth    = this.boxWidth;
        var boxHeight   = this.boxHeight;
        
        // box location
        function _locator(d) {
            return 'translate(' + self.xScale(d.x) + ',' + self.yScale(d.y+1) + ')';
        };

        // box color
        function _color (d) {
            return self.zScale(d.z);
        };
        
        // set background color
        var gBackground = svg.append('rect')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', this.options.background_color);

        // clip path
        var clip = svg.append('clipPath')
            .attr('id', 'clip')
            .append('rect')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', width)
            .attr('height', height);

        // create chart area
        var chartBody = svg.append('g')
            .attr('clip-path', 'url(#clip)');
            
        // add boxes to chart area
        var boxes = chartBody.selectAll('box-group').data(this.data, function(d, i) {
            return d.x + '\0' + d.y;
        });
        var gEnter = boxes.enter().append('g')
            .attr('class', 'box-group');
        gEnter.append('rect')
            .attr('class','heat-box');
        boxes.selectAll('rect')
            .attr('rx', 1)
            .attr('ry', 1)
            .attr('fill', _color)
            .attr('width', boxWidth)
            .attr('height', boxHeight)
            .attr('transform', _locator);
        
        // add tooltip events
        boxes.selectAll('rect')
        .on('dblclick', function(d) {
            var url = self.chart.settings.get('url_template').trim();
            if (url) {
                d3.event.stopPropagation();
                var xLabel = self.categories.array.x[d.x];
                var yLabel = self.categories.array.y[d.y];
                window.open(url.replace('__LABEL__', xLabel));
                window.open(url.replace('__LABEL__', yLabel));
            }
        })
        .on('mouseover', function(d) {
            self.tooltip.style('opacity', 0.9);
            self.tooltip .html(self._templateTooltip(d))
                .style('left', (d3.event.pageX) + 'px')
                .style('top', (d3.event.pageY - 20) + 'px');
            })
        .on('mouseout', function(d) {
            self.tooltip.style('opacity', 0);
        });

        // initially hide tooltips
        this.tooltip.style('opacity', 0);
        
        // exit
        boxes.exit().remove();
    },
    
    // x axis
    _buildX : function() {
        // link this
        var self = this;
        
        // collect parameters
        var height      = this.height;
        var width       = this.width;
        var margin      = this.options.margin;
        var svg         = this.svg;
        var font_size   = this.options.style['font-size'];
        var boxWidth    = this.boxWidth;
        
        // draw x axis
        this.gxAxis = svg.append('g')
            .attr('class', 'x axis')
            .style('stroke-width', 1)
            .attr('transform', 'translate(0,' + height + ')')
            .call(this.xAxis);
            
        // fix text
        var xFontSize = Math.min(boxWidth, font_size);
        this.gxAxis.selectAll('text')
            .style(this.options.style)
            .style({'font-size': xFontSize + 'px'})
            .attr('transform', function(d) {
                var y = -this.getBBox().height - 15;
                var x = -xFontSize + boxWidth/2;
                return 'rotate(-90)translate(' + y + ',' + x + ')';
            });
            
        // set background color
        var gxAxisLabelBackground = svg.append('rect')
            .attr('width', width)
            .attr('height', font_size + 3)
            .attr('y', height + margin.bottom - font_size - 3)
            .attr('fill', this.options.debug_color)
            .attr('opacity', 0.7);
            
        // axis label
        this.gxAxisLabel = svg.append('text')
            .attr('class', 'x label')
            .style(this.options.style)
            .text(this.chart.settings.get('x_axis_label'))
            .attr('transform', function(d) {
                var y = height + margin.bottom - font_size/3;
                var x = (width - this.getBBox().width)/2;
                return 'translate(' + x + ',' + y + ')';
            });
            
        // chart title
        this.gxTickLabel = svg.append('text')
            .attr('class', 'title')
            .style(this.options.style)
            .style({'font-size' : 1.5*font_size})
            .text(this.group.key)
            .attr('transform', function(d) {
                var y = -margin.top/2;
                var x = (width - this.getBBox().width)/2;
                return 'translate(' + x + ',' + y + ')';
            });
    },
    
    // y axis
    _buildY : function() {
        // link this
        var self = this;
        
        // collect parameters
        var height      = this.height;
        var width       = this.width;
        var margin      = this.options.margin;
        var svg         = this.svg;
        var font_size   = this.options.style['font-size'];
        var boxHeight   = this.boxHeight;
        
        // draw y axis
        this.gyAxis = svg.append('g')
            .attr('class', 'y axis')
            .style('stroke-width', 1)
            .call(this.yAxis);

        // fix text
        var yFontSize = Math.min(boxHeight, font_size);
        this.gyAxis.selectAll('text')
            .style(this.options.style)
            .style({'font-size': yFontSize + 'px'})
            .attr('y', -boxHeight/2);
        
        // set background color
        var gyAxisLabelBackground = svg.append('rect')
            .attr('width', font_size)
            .attr('height', height)
            .attr('x', -margin.left)
            .attr('fill', this.options.debug_color)
            .attr('opacity', 0.7);
            
        // axis label
        this.gyAxisLabel = svg.append('text')
            .attr('class', 'y label')
            .style(this.options.style)
            .text(this.chart.settings.get('y_axis_label'))
            .attr('transform', function(d) {
                var x = -margin.left + font_size-2;
                var y = -(height + this.getBBox().width)/2;
                return 'rotate(-90)translate(' + y + ',' + x + ')';
            });
    },

    // legend
    _buildLegend : function() {
        // link this
        var self = this;
        
        // collect parameters
        var height      = this.height;
        var width       = this.width;
        var margin      = this.options.margin;
        var font_size   = this.options.legend.style['font-size'];
        var limit       = this.options.legend.limit;
                
        // identify legend dimensions
        var legendSize  = this.options.legend.size;
        var legendWidth = this.options.legend.width;
        var legendElements = this.zScale.range().length;
        var legendElementHeight = Math.max(legendSize * height / legendElements, font_size);
        var legendHeight = legendElements * legendElementHeight / 2;
        
        // check number of legend elements
        var data = d3.range(this.zMin, this.zMax, 2 * (this.zMax-this.zMin) / legendElements).reverse();
        if (data.length < 2) {
            return;
        }
        
        // create legend elements
        var legend = this.svg.selectAll('.legend')
            .data(data)
            .enter().append('g')
                .attr('class', 'legend')
                .attr('transform', function(d, i) {
                    var x = width + 10;
                    var y = ((height - legendHeight) / 2) + (i * legendElementHeight);
                    return 'translate(' + x + ',' + y + ')';
                });

        legend.append('rect')
            .attr('width', legendWidth)
            .attr('height', legendElementHeight)
            .style('fill', function(z) {
                return self.zScale(z);
            });

        legend.append('text')
            .attr('x', legendWidth + 4)
            .attr('y', function() {
                return (legendElementHeight+this.getBBox().height)/2;
            })
            .style(this.options.legend.style)
            .text(function(d) {
                var str = String(d);
                if (str.length > limit) {
                    return str.substr(0, limit-2) + '..';
                } else {
                    return str;
                }
            });
            
        this.svg.append('text')
            .style(this.options.legend.style)
            .style({'font-size' : 9, 'font-weight': 'bold'})
            .text('Legend')
            .attr('transform', function(d, i) {
                var x = width + (margin.right - this.getBBox().width) / 2;
                var y = ((height - legendHeight) / 2) - 10;
                return 'translate(' + x + ',' + y + ')';
            });
    },
    
    // create axes formatting
    _makeTickFormat: function(id) {
        var settings = this.chart.settings;
        var self = this;
        Tools.makeTickFormat({
            categories  : self.categories.array[id],
            type        : settings.get(id + '_axis_type'),
            precision   : settings.get(id + '_axis_precision'),
            formatter   : function(formatter) {
                if (formatter) {
                    self[id + 'Axis'].tickFormat(function(value) {
                       return formatter(value);
                    });
                }
            }
        });
    },
    
    // handle error
    _handleError: function(err) {
        this.chart.state('failed', err);
    },
    
    // templates
    _templateTooltip: function(d) {
        // collect data values
        var x = this.categories.array.x[d.x];
        var y = this.categories.array.y[d.y];
        var z = d.z;
        
        // create tooltip
        var tmpl =  '<table>' +
                        '<tr>' +
                            '<td class="charts-tooltip-first">Row:</td>' +
                            '<td>' + y + '</td>' +
                        '</tr>' +
                        '<tr>' +
                            '<td class="charts-tooltip-first">Column:</td>' +
                            '<td>' + x + '</td>' +
                        '</tr>' +
                        '<tr>' +
                            '<td class="charts-tooltip-first">Value:</td>' +
                            '<td>' + z + '</td>' +
                        '</tr>' +
                    '</table>';
        return tmpl;
    }
});

});