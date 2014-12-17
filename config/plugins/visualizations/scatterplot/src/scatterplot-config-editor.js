/* =============================================================================
todo:
    localize
    import button(display), func(model) - when user doesn't match
    Move margins into wid/hi calcs (so final svg dims are w/h)
    Better separation of AJAX in scatterplot.js (maybe pass in function?)
    Labels should auto fill in chart control when dataset has column_names
    Allow column selection/config using the peek output as a base for UI
    Allow setting perPage in chart controls
    Allow option to auto set width/height based on screen real estate avail.
    Handle large number of pages better (Known genes hg19)
    Use d3.nest to allow grouping, pagination/filtration by group (e.g. chromCol)
    Semantic HTML (figure, caption)
    Save as SVG/png
    Does it work w/ Galaxy.Frame?
    Embedding
    Small multiples
    Drag & Drop other splots onto current (redraw with new axis and differentiate the datasets)
    Remove 'chart' namessave
    Somehow link out from info box?
    
    Subclass on specific datatypes? (vcf, cuffdiff, etc.)
    What can be common/useful to other visualizations?

============================================================================= */
/**
 *  Scatterplot config control UI as a backbone view
 *      handles:
 *          configuring which data will be used
 *          configuring the plot display
 */
var ScatterplotConfigEditor = Backbone.View.extend({
    //TODO: !should be a view on a visualization model
    //logger      : console,
    className   : 'scatterplot-control-form',
    
    /** initialize requires a configuration Object containing a dataset Object */
    initialize : function( attributes ){
        if( !this.model ){
            this.model = new Visualization({ type: 'scatterplot' });
        }
        //this.log( this + '.initialize, attributes:', attributes );

        if( !attributes || !attributes.dataset ){
            throw new Error( "ScatterplotConfigEditor requires a dataset" );
        }
        this.dataset = attributes.dataset;
        //this.log( 'dataset:', this.dataset );

        this.display = new ScatterplotDisplay({
            dataset : attributes.dataset,
            model   : this.model
        });
    },

    // ------------------------------------------------------------------------- CONTROLS RENDERING
    render : function(){
        //console.log( this + '.render' );
        // render the tab controls, areas and loading indicator
        this.$el.empty().append( ScatterplotConfigEditor.templates.mainLayout({}));
        if( this.model.id ){
            this.$el.find( '.copy-btn' ).show();
            this.$el.find( '.save-btn' ).text( 'Update saved' );
        }
        this.$el.find( '[title]' ).tooltip();

        // render the tab content
        this._render_dataControl();
        this._render_chartControls();
        this._render_chartDisplay();

        // set up behaviours

        // auto render if given both x, y column choices
        var config = this.model.get( 'config' );
        if( this.model.id && _.isFinite( config.xColumn ) && _.isFinite( config.yColumn ) ){
            this.renderChart();
        }
        return this;
    },

    /** get an object with arrays keyed with possible column types (numeric, text, all)
     *      and if metadata_column_types is set on the dataset, add the indeces of each
     *      column into the appropriate array.
     *  Used to disable certain columns from being selected for x, y axes.
     */
    _getColumnIndecesByType : function(){
        //TODO: not sure these contraints are necc. now
        var types = {
            numeric : [],
            text    : [],
            all     : []
        };
        _.each( this.dataset.metadata_column_types || [], function( type, i ){
            if( type === 'int' || type === 'float' ){
                types.numeric.push( i );
            } else if( type === 'str' || type === 'list' ){
                types.text.push( i );
            }
            types.all.push( i );
        });
        if( types.numeric.length < 2 ){
            types.numeric = [];
        }
        //console.log( 'types:', JSON.stringify( types ) );
        return types;
    },

    /** controls for which columns are used to plot datapoints (and ids/additional info to attach if desired) */
    _render_dataControl : function( $where ){
        $where = $where || this.$el;
        var editor  = this,
            //column_names = dataset.metadata_column_names || [],
            config  = this.model.get( 'config' ),
            columnTypes = this._getColumnIndecesByType();

        // render the html
        var $dataControl = $where.find( '.tab-pane#data-control' );
        $dataControl.html( ScatterplotConfigEditor.templates.dataControl({
            peek : this.dataset.peek
        }));

        $dataControl.find( '.peek' ).peekColumnSelector({
            controls : [
                { label: 'X Column',  id: 'xColumn',  selected: config.xColumn, disabled: columnTypes.text },
                { label: 'Y Column',  id: 'yColumn',  selected: config.yColumn, disabled: columnTypes.text },
                { label: 'ID Column', id: 'idColumn', selected: config.idColumn }
            ]
            //renameColumns       : true

        }).on( 'peek-column-selector.change', function( ev, data ){
            //console.info( 'new selection:', data );
            editor.model.set( 'config', data );

        }).on( 'peek-column-selector.rename', function( ev, data ){
            //console.info( 'new column names', data );
        });

        $dataControl.find( '[title]' ).tooltip();
        return $dataControl;
    },
    
    /** tab content to control how the chart is rendered (data glyph size, chart size, etc.) */
    _render_chartControls : function( $where ){
//TODO: as controls on actual chart
        $where = $where || this.$el;
        var editor = this,
            config = this.model.get( 'config' ),
            $chartControls = $where.find( '#chart-control' );
            
        // ---- skeleton/form for controls
        $chartControls.html( ScatterplotConfigEditor.templates.chartControl( config ) );
        //console.debug( '$chartControl:', $chartControls );

        // ---- slider controls
        // limits for controls (by control/chartConfig id)
        var controlRanges = {
                'datapointSize' : { min: 2, max: 10, step: 1 },
                'width'         : { min: 200, max: 800, step: 20 },
                'height'        : { min: 200, max: 800, step: 20 }
            };

        function onSliderChange(){
            // set the model config when changed and update the slider output text
            var $this = $( this ),
                //note: returns a number nicely enough
                newVal = $this.slider( 'value' );
            // parent of slide event target has html5 attr data-config-key
            editor.model.set( 'config', _.object([[ $this.parent().data( 'config-key' ), newVal ]]) );
            $this.siblings( '.slider-output' ).text( newVal );
        }

        //console.debug( 'numeric sliders:', $chartControls.find( '.numeric-slider-input' ) );
        $chartControls.find( '.numeric-slider-input' ).each( function(){
            // set up the slider with control ranges, change event; set output text to initial value
            var $this = $( this ),
                configKey = $this.attr( 'data-config-key' ),
                sliderSettings = _.extend( controlRanges[ configKey ], {
                    value   : config[ configKey ],
                    change  : onSliderChange,
                    slide   : onSliderChange
                });
            //console.debug( configKey + ' slider settings:', sliderSettings );
            $this.find( '.slider' ).slider( sliderSettings );
            $this.children( '.slider-output' ).text( config[ configKey ] );
        });

        // ---- axes labels
        var columnNames = this.dataset.metadata_column_names || [];
        var xLabel = config.xLabel || columnNames[ config.xColumn ] || 'X';
        var yLabel = config.yLabel || columnNames[ config.yColumn ] || 'Y';
        // set label inputs to current x, y metadata_column_names (if any)
        $chartControls.find( 'input[name="X-axis-label"]' ).val( xLabel )
            .on( 'change', function(){
                editor.model.set( 'config', { xLabel: $( this ).val() });
            });
        $chartControls.find( 'input[name="Y-axis-label"]' ).val( yLabel )
            .on( 'change', function(){
                editor.model.set( 'config', { yLabel: $( this ).val() });
            });

        //console.debug( '$chartControls:', $chartControls );
        $chartControls.find( '[title]' ).tooltip();
        return $chartControls;
    },

    /** render the tab content where the chart is displayed (but not the chart itself) */
    _render_chartDisplay : function( $where ){
        $where = $where || this.$el;
        var $chartDisplay = $where.find( '.tab-pane#chart-display' );
        this.display.setElement( $chartDisplay );
        this.display.render();

        $chartDisplay.find( '[title]' ).tooltip();
        return $chartDisplay;
    },

    // ------------------------------------------------------------------------- EVENTS
    events : {
        'change #include-id-checkbox'          : 'toggleThirdColumnSelector',
        'click #data-control .render-button'   : 'renderChart',
        'click #chart-control .render-button'  : 'renderChart',
        'click .save-btn'                      : 'saveVisualization',
        //'click .copy-btn'                       : function(e){ this.model.save(); }
    },

    saveVisualization : function(){
        var editor = this;
        this.model.save()
            .fail( function( xhr, status, message ){
                console.error( xhr, status, message );
                editor.trigger( 'save:error', view );
                alert( 'Error loading data:\n' + xhr.responseText );
            })
            .then( function(){
                editor.display.render();
            });
    },

    toggleThirdColumnSelector : function(){
        // show/hide the id selector on the data settings panel
        this.$el.find( 'select[name="idColumn"]' ).parent().toggle();
    },

    // ------------------------------------------------------------------------- CHART/STATS RENDERING
    renderChart : function(){
        //console.log( this + '.renderChart' );
        // fetch the data, (re-)render the chart
        this.$el.find( '.nav li.disabled' ).removeClass( 'disabled' );
        this.$el.find( 'ul.nav' ).find( 'a[href="#chart-display"]' ).tab( 'show' );
        this.display.fetchData();
        //console.debug( this.display.$el );
    },

    toString : function(){
        return 'ScatterplotConfigEditor(' + (( this.dataset )?( this.dataset.id ):( '' )) + ')';
    }
});

ScatterplotConfigEditor.templates = {
    mainLayout      : scatterplot.editor,
    dataControl     : scatterplot.datacontrol,
    chartControl    : scatterplot.chartcontrol
};

//==============================================================================
