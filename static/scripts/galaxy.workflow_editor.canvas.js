/** TODO:
  * Mapping over collections...
  * On update node - collection mapping GUI goes away
  */
function CollectionTypeDescription( collection_type ) {
    this.collection_type = collection_type;
    this.is_collection = true;
}


$.extend( CollectionTypeDescription.prototype, {
    canMatch: function( other_collection_type_description ) {
        if( other_collection_type_description === NULL_CONNECTION_TYPE_DESCRIPTION ) {
            return false;
        }
        if( other_collection_type_description === ANY_COLLECTION_TYPE_DESCRIPTION ) {
            return true;
        }
        return other_collection_type_description.collection_type == this.collection_type;
    },
    canMapOver: function( other_collection_type_description ) {
        if( other_collection_type_description === NULL_CONNECTION_TYPE_DESCRIPTION ) {
            return false;
        }
        if( other_collection_type_description === ANY_COLLECTION_TYPE_DESCRIPTION ) {
            return false;
        }
        return this._endsWith( this.collection_type, other_collection_type_description.collection_type );
    },
    effectiveMapOver: function( other_collection_type_description ) {
        var other_collection_type = other_collection_type_description.collection_type;
        var effective_collection_type = this.collection_type.substring( 0, this.collection_type.length - other_collection_type.length - 1 );
        return new CollectionTypeDescription( effective_collection_type );
    },
    toString: function() {
        return "CollectionType[" + this.collection_type + "]";
    },
    _endsWith: function( str, suffix ) {
        return str.indexOf(suffix, str.length - suffix.length) !== -1;
    }
} );

NULL_CONNECTION_TYPE_DESCRIPTION = {
    is_collection: false,
    canMatch: function( other ) { return false; },
    canMapOver: function( other_collection_type ) {
        return false;
    },
    toString: function() {
        return "NullCollectionType[]";
    },
};

ANY_COLLECTION_TYPE_DESCRIPTION = {
    is_collection: true,
    canMatch: function( other ) { return NULL_CONNECTION_TYPE_DESCRIPTION !== other; },
    canMapOver: function( other_collection_type ) {
        return false;
    },
    toString: function() {
        return "AnyCollectionType[]";
    },
};

var TerminalMapping = Backbone.Model.extend( {
    initialize: function( attr ) {
        this.mapOver = attr.mapOver || NULL_CONNECTION_TYPE_DESCRIPTION;
        this.terminal = attr.terminal;
        this.terminal.terminal_mapping = this;
    },
    disableMapOver: function() {
        this.mapOver = NULL_CONNECTION_TYPE_DESCRIPTION;
        this.trigger("change");
    },
    forceDisableMapOver: function() {
        this.mapOver = NULL_CONNECTION_TYPE_DESCRIPTION;
        this.trigger("change");
    }
} );

var TerminalMappingView = Backbone.View.extend( {
    tagName: "div",
    className: "fa-icon-button fa fa-folder-o",

    initialize: function( options ) {
        var map_text = "Run tool in parallel over collection";
        this.$el.tooltip({delay: 500, title: map_text });
        this.model.bind("change", _.bind(this.render, this));
    },

    render: function() {
        if( this.model.mapOver.is_collection ) {
            this.$el.show();
        } else {
            this.$el.hide();
        }
    },

} );

var InputTerminalMappingView = TerminalMappingView.extend( {
    events: {
        "click": "onClick",
    },
    onClick: function( e ) {
        if( this.model.mapOver.is_collection ) {
            // TODO: Prompt.
            this.model.forceDisableMapOver();
            this.model.terminal.node.forceDisconnectOutputs();
        }
    },
    redraw: function() {
        this.reset_icon_element();
        if( this.mapOver.is_collection ) {
            this.icon_element.addClass( "fa-icon-button fa fa-folder-o" );
            var map_text = "Run tool in parallel over " + this.mapOver.collection_type;
            this.icon_element.tooltip({delay: 500, title: map_text });
        } else {
            this.icon_element.addClass( "fa-icon-button fa fa-file-o" );
        }
    },

} );

var InputTerminalMapping = TerminalMapping;
var InputCollectionTerminalMapping = TerminalMapping;
var OutputTerminalMapping = TerminalMapping;
var OutputTerminalMappingView = TerminalMappingView;
var InputCollectionTerminalMappingView = InputTerminalMappingView;

function Terminal( element ) {
    this.element = element;
    this.connectors = [];
}
$.extend( Terminal.prototype, {
    connect: function ( connector ) {
        this.connectors.push( connector );
        if ( this.node ) {
            this.node.changed();
        }
    },
    disconnect: function ( connector ) {
        this.connectors.splice( $.inArray( connector, this.connectors ), 1 );
        if ( this.node ) {
            this.node.changed();
            this.resetMappingIfNeeded();
        }
    },
    redraw: function () {
        $.each( this.connectors, function( _, c ) {
            c.redraw();  
        });
    },
    destroy: function () {
        $.each( this.connectors.slice(), function( _, c ) {
            c.destroy();
        });
    },
    setMapOver : function( val ) {
        if( this.multiple ) {
            return; // Cannot set this to be multirun...
        }

        if( this.terminal_mapping.mapOver != val ) {
            this.terminal_mapping.mapOver = val;
            this.terminal_mapping.trigger("change");
            for( var output_name in this.node.output_terminals ) {
                var terminal = this.node.output_terminals[ output_name ];
                terminal.setMapOver( val );
            }
        }
    },
    mapOver: function( ) {
        if (! this.terminal_mapping ) {
            return NULL_CONNECTION_TYPE_DESCRIPTION;
        } else {
            return this.terminal_mapping.mapOver;
        }
    },
    resetMapping: function() {
        this.terminal_mapping.disableMapOver();
    },

    resetMappingIfNeeded: function( ) {}, // Subclasses should override this...

});

function OutputTerminal( element, datatypes ) {
    Terminal.call( this, element );
    this.datatypes = datatypes;
    this.is_data_input = false;

    if( datatypes ) {
        var first_datatype = datatypes[ 0 ];
        if( first_datatype == "input" ) {
            this.is_data_input = true;
        }
    }
}

OutputTerminal.prototype = new Terminal();


$.extend( OutputTerminal.prototype, {

    resetMappingIfNeeded: function( ) {
        if( !this.node.hasMappedOverInputTerminals() ) {
            this.terminal_mapping.disableMapOver();
        }
    },

    disconnectAll: function( ) {
        _.each( this.connectors, function( connector ) {
            connector.destroy();
        } );
    }

});


// Base class for input terminals and input collection terminals...
function BaseInputTerminal( element ) {
    Terminal.call( this, element );
}

BaseInputTerminal.prototype = new Terminal();

$.extend( BaseInputTerminal.prototype, {
    can_accept: function ( other ) {
        var inputFilled = this.inputFilled();
        if( inputFilled ) {
            return false;
        }
        return this.canAttach( other );
    },
    inputFilled: function() {
        var input_filled;
        if( this.multiple ) {
            if( this.connectors.length === 0 ) {
                input_filled = false;
            } else {
                var first_output = this.connectors[ 0 ].handle1;
                if( first_output === null ){
                    input_filled = false;
                } else {
                    if( first_output.is_data_collection_input || first_output.mapOver().is_collection || first_output.datatypes.indexOf( "input_collection" ) > 0 ) {
                        input_filled = true;
                    } else {
                        input_filled = false;
                    }
                }
            }
        } else {
            input_filled = this.connectors.length > 0;
        }
        return input_filled;
    },
    _otherCollectionType: function( other ) {
        var other_collection_type = NULL_CONNECTION_TYPE_DESCRIPTION;
        if( other.is_data_collection_input ) {
            other_collection_type = other.collection_type;
        } else {
            var otherMapOver = other.mapOver();
            if( otherMapOver.is_collection ) {
                other_collection_type = otherMapOver;
            }
        }
        return other_collection_type;
    },
} );


function InputTerminal( element, datatypes, multiple ) {
    BaseInputTerminal.call( this, element );
    this.datatypes = datatypes;
    this.multiple = multiple
    this.collection = false;
}

InputTerminal.prototype = new BaseInputTerminal();

$.extend( InputTerminal.prototype, {
    connect: function( connector ) {
        Terminal.prototype.connect.call( this, connector );
        var other_output = connector.handle1;
        if( ! other_output ) {
            return;
        }
        var other_collection_type = this._otherCollectionType( other_output );
        if( other_collection_type.is_collection ) {
            this.setMapOver( other_collection_type );
        }
    },
    mapping_constraints: function( ) {
        // If this is a disconnected terminal, return list of collection types
        // other terminals connected to node are constraining mapping to.
        if( ! this.node ) {
            return [];
        }
        var mapOver = this.mapOver();
        if( mapOver.is_collection ) {
            return [ mapOver ];
        }
        var connected_outputs = this.node.connectedOutputTerminals();
        var constraints = [];
        _.each( connected_outputs, function( terminal ) {
            console.log( terminal );
            if( ! terminal.mapOver().is_collection ) {
                constraints.push( NULL_CONNECTION_TYPE_DESCRIPTION );
            }
        } );
        if( constraints.length > 0 ) {
            return constraints;
        }
        var mapped_inputs = this.node.connectedMappedInputTerminals();
        if( mapped_inputs.length > 0 ) {
            return $.map( function( terminal) { return terminal.mapOver(); }, mapped_inputs );
        }
        return [];
    },
    resetMapping: function() {
        console.log( "Reset mapping on input terminal");
        this.terminal_mapping.disableMapOver();
        if( ! this.node.hasMappedOverInputTerminals() ) {
            _.each( this.node.output_terminals, function( terminal) {
                // This shouldn't be called if there are mapped over
                // outputs.
                terminal.resetMapping();
            } );
        }
    },
    resetMappingIfNeeded: function( ) {
        var mapOver = this.mapOver();
        if( ! mapOver.is_collection ) {
            return;
        }
        if( this.node.hasConnectedMappedInputTerminals() ) {
            // No output terminals are counting on this being mapped
            // over...
            this.resetMapping();
        }
        if( ! this.node.hasConnectedOutputTerminals() ) {
            // No downstream ramifications of unmapping this
            console.log( "Has not connected output terminals...");
            this.resetMapping();
        }
    },
    canAttach: function( other ) {
        var other_collection_type = this._otherCollectionType( other );
        var thisMapOver = this.mapOver();
        if( other_collection_type.is_collection ) {
            // TODO: Handle if this multiple....
            if( thisMapOver.is_collection ) {
                return thisMapOver.canMatch( other_collection_type );
            } else {
                //  Need to check if this would break constraints...
                var mapping_constraints = this.mapping_constraints();
                if( mapping_constraints.every( other_collection_type.canMatch ) ) {
                    return true;
                } else {
                    return false;
                }
            }
        } else if( thisMapOver.is_collection ) {
            // Attempting to match a non-collection output to an
            // explicitly collection input.
            return false;
        }
        // other is a non-collection output...
        for ( var t in this.datatypes ) {
            var cat_outputs = new Array();
            cat_outputs = cat_outputs.concat(other.datatypes);
            if (other.node.post_job_actions){
                for (var pja_i in other.node.post_job_actions){
                    var pja = other.node.post_job_actions[pja_i];
                    if (pja.action_type == "ChangeDatatypeAction" && (pja.output_name == '' || pja.output_name == other.name) && pja.action_arguments){
                        cat_outputs.push(pja.action_arguments['newtype']);
                    }
                }
            }
            // FIXME: No idea what to do about case when datatype is 'input'
            for ( var other_datatype_i in cat_outputs ) {
                if ( cat_outputs[other_datatype_i] == "input" || issubtype( cat_outputs[other_datatype_i], this.datatypes[t] ) ) {
                    return true;
                }
            }
        }
    }
});


function InputCollectionTerminal( element, collection_type ) {
    BaseInputTerminal.call( this, element );
    this.multiple = false;
    this.collection = true;
    if( collection_type ) {
        this.collection_type = new CollectionTypeDescription( collection_type );
    } else {
        this.collection_type = ANY_COLLECTION_TYPE_DESCRIPTION;
    }
}

InputCollectionTerminal.prototype = new BaseInputTerminal();

$.extend( InputCollectionTerminal.prototype, {
    connect: function( connector ) {
        Terminal.prototype.connect.call( this, connector );
        var other_output = connector.handle1;
        if( ! other_output ) {
            return;
        }
        var collectionType = this.collection_type;
        var otherCollectionType = this._otherCollectionType( other_output );
        if( ! collectionType.canMatch( otherCollectionType ) ) {
            this.setMapOver( otherCollectionType.effectiveMapOver( collectionType ) );
        }
    },
    canAttach: function ( other ) {
        var cat_outputs = [];
        cat_outputs = cat_outputs.concat( other.datatypes );
        var collectionType = this.collection_type;
        var otherCollectionType = this._otherCollectionType( other );
        if ( otherCollectionType.is_collection ) {
            return collectionType.canMatch( otherCollectionType ) || otherCollectionType.canMapOver( collectionType );
        }
        return false;
    }
});

function OutputCollectionTerminal( element, datatypes, collection_type ) {
    Terminal.call( this, element );
    this.collection_type = new CollectionTypeDescription( collection_type );
    this.is_data_collection_input = true;
}

OutputCollectionTerminal.prototype = new Terminal();

function Connector( handle1, handle2 ) {
    this.canvas = null;
    this.dragging = false;
    this.inner_color = "#FFFFFF";
    this.outer_color = "#D8B365";
    if ( handle1 && handle2 ) {
        this.connect( handle1, handle2 );
    }
}
$.extend( Connector.prototype, {
    connect: function ( t1, t2 ) {
        this.handle1 = t1;
        if ( this.handle1 ) {
            this.handle1.connect( this );
        }
        this.handle2 = t2;
        if ( this.handle2 ) {
            this.handle2.connect( this );
        }
    },
    destroy : function () {
        if ( this.handle1 ) {
            this.handle1.disconnect( this );
        }
        if ( this.handle2 ) {
            this.handle2.disconnect( this );
        }
        $(this.canvas).remove();
    },
    redraw : function () {
        var canvas_container = $("#canvas-container");
        if ( ! this.canvas ) {
            this.canvas = document.createElement( "canvas" );
            // excanvas specific hack
            if ( window.G_vmlCanvasManager ) {
                G_vmlCanvasManager.initElement( this.canvas );
            }
            canvas_container.append( $(this.canvas) );
            if ( this.dragging ) {
                this.canvas.style.zIndex = "300";
            }
        }
        var relativeLeft = function( e ) {
            return $(e).offset().left - canvas_container.offset().left;
        };
        var relativeTop = function( e ) {
            return $(e).offset().top - canvas_container.offset().top;
        };
        if (!this.handle1 || !this.handle2) {
            return;
        }
        // Find the position of each handle
        var start_x = relativeLeft( this.handle1.element ) + 5;
        var start_y = relativeTop( this.handle1.element ) + 5;
        var end_x = relativeLeft( this.handle2.element ) + 5;
        var end_y = relativeTop( this.handle2.element ) + 5;
        // Calculate canvas area
        var canvas_extra = 100;
        var canvas_min_x = Math.min( start_x, end_x );
        var canvas_max_x = Math.max( start_x, end_x );
        var canvas_min_y = Math.min( start_y, end_y );
        var canvas_max_y = Math.max( start_y, end_y );
        var cp_shift = Math.min( Math.max( Math.abs( canvas_max_y - canvas_min_y ) / 2, 100 ), 300 );
        var canvas_left = canvas_min_x - canvas_extra;
        var canvas_top = canvas_min_y - canvas_extra;
        var canvas_width = canvas_max_x - canvas_min_x + 2 * canvas_extra;
        var canvas_height = canvas_max_y - canvas_min_y + 2 * canvas_extra;
        // Place the canvas
        this.canvas.style.left = canvas_left + "px";
        this.canvas.style.top = canvas_top + "px";
        this.canvas.setAttribute( "width", canvas_width );
        this.canvas.setAttribute( "height", canvas_height );
        // Adjust points to be relative to the canvas
        start_x -= canvas_left;
        start_y -= canvas_top;
        end_x -= canvas_left;
        end_y -= canvas_top;
        // Draw the line

        var c = this.canvas.getContext("2d"),
            start_offsets = null,
            end_offsets = null;
        var num_offsets = 1;
        if ( this.handle1 && this.handle1.mapOver().is_collection ) {
            var start_offsets = [ -6, -3, 0, 3, 6 ];
            num_offsets = 5;
        } else {
            var start_offsets = [ 0 ];
        }
        if ( this.handle2 && this.handle2.mapOver().is_collection ) {
            var end_offsets = [ -6, -3, 0, 3, 6 ];
            num_offsets = 5;
        } else {
            var end_offsets = [ 0 ];
        }
        var connector = this;
        for( var i = 0; i < num_offsets; i++ ) {
            var inner_width = 5,
                outer_width = 7;
            if( start_offsets.length > 1 || end_offsets.length > 1 ) {
                // We have a multi-run, using many lines, make them small.
                inner_width = 1;
                outer_width = 3;
            }
            connector.draw_outlined_curve( start_x, start_y, end_x, end_y, cp_shift, inner_width, outer_width, start_offsets[ i % start_offsets.length ], end_offsets[ i % end_offsets.length ] ); 
        }
    },
    draw_outlined_curve : function( start_x, start_y, end_x, end_y, cp_shift, inner_width, outer_width, offset_start, offset_end ) {
        var offset_start = offset_start || 0;
        var offset_end = offset_end || 0;
        var c = this.canvas.getContext("2d");
        c.lineCap = "round";
        c.strokeStyle = this.outer_color;
        c.lineWidth = outer_width;
        c.beginPath();
        c.moveTo( start_x, start_y + offset_start );
        c.bezierCurveTo( start_x + cp_shift, start_y + offset_start, end_x - cp_shift, end_y + offset_end, end_x, end_y + offset_end);
        c.stroke();
        // Inner line
        c.strokeStyle = this.inner_color;
        c.lineWidth = inner_width;
        c.beginPath();
        c.moveTo( start_x, start_y + offset_start );
        c.bezierCurveTo( start_x + cp_shift, start_y + offset_start, end_x - cp_shift, end_y + offset_end, end_x, end_y + offset_end );
        c.stroke();
    }
} );

function Node( element ) {
    this.element = element;
    this.input_terminals = {};
    this.output_terminals = {};
    this.tool_errors = {};
}

$.extend( Node.prototype, {
    connectedOutputTerminals: function() {
        var connected_outputs = [];
        $.each( this.output_terminals, function( _, t ) {
            if( t.connectors.length > 0 ) {
                connected_outputs.push( t );
            }
        } );
        return connected_outputs;
    },
    hasConnectedOutputTerminals: function() {
        return this.connectedOutputTerminals().length > 0; // TODO: Optimize
    },
    connectedMappedOutputTerminals: function() { // Unused
        return this._connectedMappedTerminals( this.output_terminals );
    },
    connectedMappedInputTerminals: function() {
        return this._connectedMappedTerminals( this.input_terminals );
    },
    hasConnectedMappedInputTerminals: function() {
        return this.connectedMappedInputTerminals().length > 0;
    },
    _connectedMappedTerminals: function( all_terminals ) {
        var mapped_outputs = [];
        $.each( all_terminals, function( _, t ) {
            var mapOver = t.mapOver();
            if( mapOver.is_collection ) {
                if( t.connectors.length > 0 ) {
                    mapped_outputs.push( t );
                }
            }
        });
        return mapped_outputs;
    },
    hasMappedOverInputTerminals: function() {
        var found = false;
        _.each( this.input_terminals, function( t ) {
            var mapOver = t.mapOver();
            if( mapOver.is_collection ) {
                found = true;
            }
        } );
        return found;
    },
    forceDisconnectOutputs: function() {
        _.each( this.output_terminals, function( terminal ) {
            terminal.disconnectAll();
        } );
    },
    new_input_terminal : function( input ) {
        var t = $("<div class='terminal input-terminal'></div>")[ 0 ];
        this.enable_input_terminal( t, input.name, input.extensions, input.multiple, input.input_type, input.collection_type );
        return t;
    },
    enable_input_terminal : function( element, name, types, multiple, input_type, collection_type ) {
        var node = this;
        var terminal = null;
        if( input_type == "dataset_collection" ) {
            terminal = element.terminal = new InputCollectionTerminal( element, collection_type );
            var terminal_mapping = new InputCollectionTerminalMapping( { terminal: terminal } );
            var terminal_mapping_view = new InputCollectionTerminalMappingView( { model: terminal_mapping } );
            terminal_mapping_view.render();
            terminal.terminal_mapping_view = terminal_mapping_view;
        } else {
            terminal = element.terminal = new InputTerminal( element, types, multiple );
            if( !multiple ) {
                // Uber hacks ahead - move all of this to different layers when rebasing against
                // 263.
                var terminal_mapping = new InputTerminalMapping( { terminal: terminal } );
                var terminal_mapping_view = new InputTerminalMappingView( { model: terminal_mapping } );
                terminal_mapping_view.render();
                terminal.terminal_mapping_view = terminal_mapping_view;
            }
        }

        element.terminal = terminal;
        terminal.node = node;
        terminal.name = name;
        $(element).bind( "dropinit", function( e, d ) {
            // Accept a dragable if it is an output terminal and has a
            // compatible type
            return $(d.drag).hasClass( "output-terminal" ) && terminal.can_accept( d.drag.terminal );
        }).bind( "dropstart", function( e, d  ) {
            if (d.proxy.terminal) { 
                d.proxy.terminal.connectors[0].inner_color = "#BBFFBB";
            }
        }).bind( "dropend", function ( e, d ) {
            if (d.proxy.terminal) { 
                d.proxy.terminal.connectors[0].inner_color = "#FFFFFF";
            }
        }).bind( "drop", function( e, d ) {
            ( new Connector( d.drag.terminal, terminal ) ).redraw();
        }).bind( "hover", function() {
            // If connected, create a popup to allow disconnection
            if ( terminal.connectors.length > 0 ) {
                // Create callout
                var t = $("<div class='callout'></div>")
                    .css( { display: 'none' } )
                    .appendTo( "body" )
                    .append(
                        $("<div class='button'></div>").append(
                            $("<div/>").addClass("fa-icon-button fa fa-times").click( function() {
                                $.each( terminal.connectors, function( _, x ) {
                                    if (x) {
                                        x.destroy();
                                    }
                                });
                                t.remove();
                            })))
                    .bind( "mouseleave", function() {
                        $(this).remove();
                    });
                // Position it and show
                t.css({
                        top: $(element).offset().top - 2,
                        left: $(element).offset().left - t.width(),
                        'padding-right': $(element).width()
                    }).show();
            }
        });
        node.input_terminals[name] = terminal;
    },
    enable_output_terminal : function( element, name, type, collection_type ) {
        var node = this;
        var terminal_element = element;
        var terminal = null;
        if( collection_type ) {
            terminal = new OutputCollectionTerminal( element, type, collection_type );
        } else {
            terminal = new OutputTerminal( element, type );
        }
        element.terminal = terminal;
        terminal.node = node;
        terminal.name = name;
        $(element).bind( "dragstart", function( e, d ) { 
            $( d.available ).addClass( "input-terminal-active" );
            // Save PJAs in the case of change datatype actions.
            workflow.check_changes_in_active_form(); 
            // Drag proxy div
            var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' )
                .appendTo( "#canvas-container" ).get(0);
            // Terminal and connection to display noodle while dragging
            h.terminal = new OutputTerminal( h );
            var c = new Connector();
            c.dragging = true;
            c.connect( element.terminal, h.terminal );
            return h;
        }).bind( "drag", function ( e, d ) {
            var onmove = function() {
                var po = $(d.proxy).offsetParent().offset(),
                    x = d.offsetX - po.left,
                    y = d.offsetY - po.top;
                $(d.proxy).css( { left: x, top: y } );
                d.proxy.terminal.redraw();
                // FIXME: global
                canvas_manager.update_viewport_overlay();
            };
            onmove();
            $("#canvas-container").get(0).scroll_panel.test( e, onmove );
        }).bind( "dragend", function ( e, d ) {
            d.proxy.terminal.connectors[0].destroy();
            $(d.proxy).remove();
            $( d.available ).removeClass( "input-terminal-active" );
            $("#canvas-container").get(0).scroll_panel.stop();
        });
        node.output_terminals[name] = terminal;
    },
    redraw : function () {
        $.each( this.input_terminals, function( _, t ) {
            t.redraw();
        });
        $.each( this.output_terminals, function( _, t ) {
            t.redraw();
        });
    },
    destroy : function () {
        $.each( this.input_terminals, function( k, t ) {
            t.destroy();
        });
        $.each( this.output_terminals, function( k, t ) {
            t.destroy();
        });
        workflow.remove_node( this );
        $(this.element).remove();
    },
    make_active : function () {
        $(this.element).addClass( "toolForm-active" );
    },
    make_inactive : function () {
        // Keep inactive nodes stacked from most to least recently active
        // by moving element to the end of parent's node list
        var element = this.element.get(0);
        (function(p) { p.removeChild( element ); p.appendChild( element ); })(element.parentNode);
        // Remove active class
        $(element).removeClass( "toolForm-active" );
    },
    init_field_data : function ( data ) {
        var f = this.element;
        if ( data.type ) {
            this.type = data.type;
        }
        this.name = data.name;
        this.form_html = data.form_html;
        this.tool_state = data.tool_state;
        this.tool_errors = data.tool_errors;
        this.tooltip = data.tooltip ? data.tooltip : "";
        this.annotation = data.annotation;
        this.post_job_actions = data.post_job_actions ? data.post_job_actions : {};
        this.workflow_outputs = data.workflow_outputs ? data.workflow_outputs : [];

        if ( this.tool_errors ) {
            f.addClass( "tool-node-error" );
        } else {
            f.removeClass( "tool-node-error" );
        }
        var node = this;
        var output_width = Math.max(150, f.width());
        var b = f.find( ".toolFormBody" );
        b.find( "div" ).remove();
        var ibox = $("<div class='inputs'></div>").appendTo( b );
        $.each( data.data_inputs, function( i, input ) {
            var t = node.new_input_terminal( input );
            var terminal = node.input_terminals[ input.name ];
            var multiple = terminal.multiple;
            var ib = $("<div class='form-row dataRow input-data-row' name='" + input.name + "'>" + input.label + "</div>" );
            ib.css({  position:'absolute',
                        left: -1000,
                        top: -1000,
                        display:'none'});
            $('body').append(ib);
            output_width = Math.max(output_width, ib.outerWidth());
            ib.css({ position:'',
                       left:'',
                       top:'',
                       display:'' });
            ib.remove();
            if( terminal.terminal_mapping_view ) {
                ibox.append( ib.prepend( t, terminal.terminal_mapping_view.el ) );
            } else {
                ibox.append( ib.prepend( t ) );
            }
        });
        if ( ( data.data_inputs.length > 0 ) && ( data.data_outputs.length > 0 ) ) {
            b.append( $( "<div class='rule'></div>" ) );
        }
        $.each( data.data_outputs, function( i, output ) {
            var t = $( "<div class='terminal output-terminal'></div>" );
            node.enable_output_terminal( t[ 0 ], output.name, output.extensions, output.collection_type );
            var terminal = node.output_terminals[ output.name ];
            var terminal_mapping = new OutputTerminalMapping( { terminal: terminal } );
            var terminal_mapping_view = new OutputTerminalMappingView( { model: terminal_mapping } );
            terminal_mapping_view.render();
            var label = output.name;
            var isInput = output.extensions.indexOf( 'input' ) >= 0 || output.extensions.indexOf( 'input_collection' ) >= 0;
            if ( ! isInput ) {
                label = label + " (" + output.extensions.join(", ") + ")";
            }
            var r = $("<div class='form-row dataRow'>" + label + "</div>" );
            if (node.type == 'tool') {
                var callout = $("<div class='callout "+label+"'></div>")
                    .css( { display: 'none' } )
                    .append(
                        $("<div class='buttons'></div>").append(
                            $("<img/>").attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-outline.png').click( function() {
                                if ($.inArray(output.name, node.workflow_outputs) != -1){
                                    node.workflow_outputs.splice($.inArray(output.name, node.workflow_outputs), 1);
                                    callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-outline.png');
                                }else{
                                    node.workflow_outputs.push(output.name);
                                    callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small.png');
                                }
                                workflow.has_changes = true;
                                canvas_manager.draw_overview();
                            })))
                    .tooltip({delay:500, title: "Mark dataset as a workflow output. All unmarked datasets will be hidden." });
                callout.css({
                        top: '50%',
                        margin:'-8px 0px 0px 0px',
                        right: 8
                    });
                callout.show();
                r.append(callout);
                if ($.inArray(output.name, node.workflow_outputs) === -1){
                    callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-outline.png');
                }else{
                    callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small.png');
                }
                r.hover(
                    function(){
                        callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-yellow.png');
                    },
                    function(){
                        if ($.inArray(output.name, node.workflow_outputs) === -1){
                            callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small-outline.png');
                        }else{
                            callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small.png');
                        }
                    });
            }
            r.css({  position:'absolute',
                        left: -1000,
                        top: -1000,
                        display:'none'});
            $('body').append(r);
            output_width = Math.max(output_width, r.outerWidth() + 17);
            r.css({ position:'',
                       left:'',
                       top:'',
                       display:'' });
            r.detach();
            b.append( r.append( terminal_mapping_view.el, t ) );
        });
        f.css( "width", Math.min(250, Math.max(f.width(), output_width )));
        workflow.node_changed( this );
    },
    update_field_data : function( data ) {
        var el = $(this.element),
            node = this;
        this.tool_state = data.tool_state;
        this.form_html = data.form_html;
        this.tool_errors = data.tool_errors;
        this.annotation = data['annotation'];
        var pja_in = $.parseJSON(data.post_job_actions);
        this.post_job_actions = pja_in ? pja_in : {};
        if ( this.tool_errors ) {
                el.addClass( "tool-node-error" );
        } else {
                el.removeClass( "tool-node-error" );
        }
        // Update input rows
        var old_body = el.find( "div.inputs" );
        var new_body = $("<div class='inputs'></div>");
        $.each( data.data_inputs, function( i, input ) {
            var t = node.new_input_terminal( input );
            var terminal = node.input_terminals[ input.name ];
            // If already connected save old connection
            old_body.find( "div[name='" + input.name + "']" ).each( function() {
                $(this).find( ".input-terminal" ).each( function() {
                    var c = this.terminal.connectors[0];
                    if ( c ) {
                        t.terminal.connectors[0] = c;
                        c.handle2 = t.terminal;
                    }
                });
                $(this).remove();
            });
            // Append to new body
            var ib = $("<div class='form-row dataRow input-data-row' name='" + input.name + "'>" + input.label + "</div>" );
            if( ! terminal.multiple ) {
                var terminal_mapping = new InputTerminalMapping( { terminal: terminal } );
                var terminal_mapping_view = new InputTerminalMappingView( { model: terminal_mapping } );
                terminal_mapping_view.render();
                var multirun_element = terminal_mapping.element;
                new_body.append( ib.prepend( t, multirun_element ) );
            } else {
                new_body.append( ib.prepend( t ) );
            }
        });
        old_body.replaceWith( new_body );
        // Cleanup any leftover terminals
        old_body.find( "div.input-data-row > .terminal" ).each( function() {
            this.terminal.destroy();
        });
        // If active, reactivate with new form_html
        this.changed();
        this.redraw();
    },
    error : function ( text ) {
        var b = $(this.element).find( ".toolFormBody" );
        b.find( "div" ).remove();
        var tmp = "<div style='color: red; text-style: italic;'>" + text + "</div>";
        this.form_html = tmp;
        b.html( tmp );
        workflow.node_changed( this );
    },
    changed: function() {
        workflow.node_changed( this );
    },
} );

function Workflow( canvas_container ) {
    this.canvas_container = canvas_container;
    this.id_counter = 0;
    this.nodes = {};
    this.name = null;
    this.has_changes = false;
    this.active_form_has_changes = false;
}
$.extend( Workflow.prototype, {
    add_node : function( node ) {
        node.id = this.id_counter;
        node.element.attr( 'id', 'wf-node-step-' + node.id );
        this.id_counter++;
        this.nodes[ node.id ] = node;
        this.has_changes = true;
        node.workflow = this;
    },
    remove_node : function( node ) {
        if ( this.active_node == node ) {
            this.clear_active_node();
        }
        delete this.nodes[ node.id ] ;
        this.has_changes = true;
    },
    remove_all : function() {
        wf = this;
        $.each( this.nodes, function ( k, v ) {
            v.destroy();
            wf.remove_node( v );
        });
    },
    rectify_workflow_outputs : function() {
        // Find out if we're using workflow_outputs or not.
        var using_workflow_outputs = false;
        var has_existing_pjas = false;
        $.each( this.nodes, function ( k, node ) {
            if (node.workflow_outputs && node.workflow_outputs.length > 0){
                using_workflow_outputs = true;
            }
            $.each(node.post_job_actions, function(pja_id, pja){
                if (pja.action_type === "HideDatasetAction"){
                    has_existing_pjas = true;
                }
            });
        });
        if (using_workflow_outputs !== false || has_existing_pjas !== false){
            // Using workflow outputs, or has existing pjas.  Remove all PJAs and recreate based on outputs.
            $.each(this.nodes, function (k, node ){
                if (node.type === 'tool'){
                    var node_changed = false;
                    if (node.post_job_actions == null){
                        node.post_job_actions = {};
                        node_changed = true;
                    }
                    var pjas_to_rem = [];
                    $.each(node.post_job_actions, function(pja_id, pja){
                        if (pja.action_type == "HideDatasetAction"){
                            pjas_to_rem.push(pja_id);
                        }
                    });
                    if (pjas_to_rem.length > 0 ) {
                        $.each(pjas_to_rem, function(i, pja_name){
                            node_changed = true;
                            delete node.post_job_actions[pja_name];
                        });
                    }
                    if (using_workflow_outputs){
                        $.each(node.output_terminals, function(ot_id, ot){
                            var create_pja = true;
                            $.each(node.workflow_outputs, function(i, wo_name){
                                if (ot.name === wo_name){
                                    create_pja = false;
                                }
                            });
                            if (create_pja === true){
                                node_changed = true;
                                var pja = {
                                    action_type : "HideDatasetAction",
                                    output_name : ot.name,
                                    action_arguments : {}
                                }
                                node.post_job_actions['HideDatasetAction'+ot.name] = null;
                                node.post_job_actions['HideDatasetAction'+ot.name] = pja;
                            }
                        });
                    }
                    // lastly, if this is the active node, and we made changes, reload the display at right.
                    if (workflow.active_node == node && node_changed === true) {
                        workflow.reload_active_node();
                    }
                }
            });
        }
    },
    to_simple : function () {
        var nodes = {};
        $.each( this.nodes, function ( i, node ) {
            var input_connections = {};
            $.each( node.input_terminals, function ( k, t ) {
                input_connections[ t.name ] = null;
                // There should only be 0 or 1 connectors, so this is
                // really a sneaky if statement
                var cons = []
                $.each( t.connectors, function ( i, c ) {
                    cons[i] = { id: c.handle1.node.id, output_name: c.handle1.name };
                    input_connections[ t.name ] = cons;
                });
            });
            var post_job_actions = {};
            if (node.post_job_actions){
                $.each( node.post_job_actions, function ( i, act ) {
                    var pja = {
                        action_type : act.action_type, 
                        output_name : act.output_name, 
                        action_arguments : act.action_arguments
                    }
                    post_job_actions[ act.action_type + act.output_name ] = null;
                    post_job_actions[ act.action_type + act.output_name ] = pja;
                });
            }
            if (!node.workflow_outputs){
                node.workflow_outputs = [];
                // Just in case.
            }
            var node_data = {
                id : node.id,
                type : node.type,
                tool_id : node.tool_id,
                tool_state : node.tool_state,
                tool_errors : node.tool_errors,
                input_connections : input_connections,
                position : $(node.element).position(),
                annotation: node.annotation,
                post_job_actions: node.post_job_actions,
                workflow_outputs: node.workflow_outputs
            };
            nodes[ node.id ] = node_data;
        });
        return { steps: nodes };
    },
    from_simple : function ( data ) {
        wf = this;
        var max_id = 0;
        wf.name = data.name;
        // First pass, nodes
        var using_workflow_outputs = false;
        $.each( data.steps, function( id, step ) {
            var node = prebuild_node( step.type, step.name, step.tool_id );
            node.init_field_data( step );
            if ( step.position ) {
                node.element.css( { top: step.position.top, left: step.position.left } );
            }
            node.id = step.id;
            wf.nodes[ node.id ] = node;
            max_id = Math.max( max_id, parseInt( id ) );
            // For older workflows, it's possible to have HideDataset PJAs, but not WorkflowOutputs.
            // Check for either, and then add outputs in the next pass.
            if (!using_workflow_outputs && node.type === 'tool'){
                if (node.workflow_outputs.length > 0){
                    using_workflow_outputs = true;
                }
                else{
                    $.each(node.post_job_actions, function(pja_id, pja){
                        if (pja.action_type === "HideDatasetAction"){
                            using_workflow_outputs = true;
                        }
                    });
                }
            }
        });
        wf.id_counter = max_id + 1;
        // Second pass, connections
        $.each( data.steps, function( id, step ) {
            var node = wf.nodes[id];
            $.each( step.input_connections, function( k, v ) {
                if ( v ) {
                    if ( ! $.isArray( v ) ) {
                        v = [ v ];
                    }
                    $.each( v, function( l, x ) {
                        var other_node = wf.nodes[ x.id ];
                        var c = new Connector();
                        c.connect( other_node.output_terminals[ x.output_name ],
                                   node.input_terminals[ k ] );
                        c.redraw();
                    });
                }
            });
            if(using_workflow_outputs && node.type === 'tool'){
                // Ensure that every output terminal has a WorkflowOutput or HideDatasetAction.
                $.each(node.output_terminals, function(ot_id, ot){
                    if(node.post_job_actions['HideDatasetAction'+ot.name] === undefined){
                        node.workflow_outputs.push(ot.name);
                        callout = $(node.element).find('.callout.'+ot.name);
                        callout.find('img').attr('src', galaxy_config.root + 'static/images/fugue/asterisk-small.png');
                        workflow.has_changes = true;
                    }
                });
            }
        });
    },
    check_changes_in_active_form : function() {
        // If active form has changed, save it
        if (this.active_form_has_changes) {
            this.has_changes = true;
            // Submit form.
            $("#right-content").find("form").submit();
            this.active_form_has_changes = false;
        }
    },
    reload_active_node : function() {
        if (this.active_node){
            var node = this.active_node;
            this.clear_active_node();
            this.activate_node(node);
        }
    },
    clear_active_node : function() {
        if ( this.active_node ) {
            this.active_node.make_inactive();
            this.active_node = null;
        }
        parent.show_form_for_tool( "<div>No node selected</div>" );
    },
    activate_node : function( node ) {
        if ( this.active_node != node ) {
            this.check_changes_in_active_form();
            this.clear_active_node();
            parent.show_form_for_tool( node.form_html + node.tooltip, node );
            node.make_active();
            this.active_node = node;
        }
    },
    node_changed : function ( node ) {
        this.has_changes = true;
        if ( this.active_node == node ) {
            // Reactive with new form_html
            this.check_changes_in_active_form(); //Force changes to be saved even on new connection (previously dumped)
            parent.show_form_for_tool( node.form_html + node.tooltip, node );
        }
    },
    layout : function () {
        this.check_changes_in_active_form();
        this.has_changes = true;
        // Prepare predecessor / successor tracking
        var n_pred = {};
        var successors = {};
        // First pass to initialize arrays even for nodes with no connections
        $.each( this.nodes, function( id, node ) {
            if ( n_pred[id] === undefined ) { n_pred[id] = 0; }
            if ( successors[id] === undefined ) { successors[id] = []; }
        });
        // Second pass to count predecessors and successors
        $.each( this.nodes, function( id, node ) {
            $.each( node.input_terminals, function ( j, t ) {
                $.each( t.connectors, function ( k, c ) {
                    // A connection exists from `other` to `node`
                    var other = c.handle1.node;
                    // node gains a predecessor
                    n_pred[node.id] += 1;
                    // other gains a successor
                    successors[other.id].push( node.id );
                });
            });
        });
        // Assemble order, tracking levels
        node_ids_by_level = [];
        while ( true ) {
            // Everything without a predecessor
            level_parents = [];
            for ( var pred_k in n_pred ) {
                if ( n_pred[ pred_k ] == 0 ) {
                    level_parents.push( pred_k );
                }
            }        
            if ( level_parents.length == 0 ) {
                break;
            }
            node_ids_by_level.push( level_parents );
            // Remove the parents from this level, and decrement the number
            // of predecessors for each successor
            for ( var k in level_parents ) {
                var v = level_parents[k];
                delete n_pred[v];
                for ( var sk in successors[v] ) {
                    n_pred[ successors[v][sk] ] -= 1;
                }
            }
        }
        if ( n_pred.length ) {
            // ERROR: CYCLE! Currently we do nothing
            return;
        }
        // Layout each level
        var all_nodes = this.nodes;
        var h_pad = 80; v_pad = 30;
        var left = h_pad;        
        $.each( node_ids_by_level, function( i, ids ) {
            // We keep nodes in the same order in a level to give the user
            // some control over ordering
            ids.sort( function( a, b ) {
                return $(all_nodes[a].element).position().top - $(all_nodes[b].element).position().top;
            });
            // Position each node
            var max_width = 0;
            var top = v_pad;
            $.each( ids, function( j, id ) {
                var node = all_nodes[id];
                var element = $(node.element);
                $(element).css( { top: top, left: left } );
                max_width = Math.max( max_width, $(element).width() );
                top += $(element).height() + v_pad;
            });
            left += max_width + h_pad;
        });
        // Need to redraw all connectors
        $.each( all_nodes, function( _, node ) { node.redraw(); } );
    },
    bounds_for_all_nodes: function() {
        var xmin = Infinity, xmax = -Infinity,
            ymin = Infinity, ymax = -Infinity,
            p;
        $.each( this.nodes, function( id, node ) {
            e = $(node.element);
            p = e.position();
            xmin = Math.min( xmin, p.left );
            xmax = Math.max( xmax, p.left + e.width() );
            ymin = Math.min( ymin, p.top );
            ymax = Math.max( ymax, p.top + e.width() );
        });
        return  { xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax };
    },
    fit_canvas_to_nodes: function() {
        // Span of all elements
        var bounds = this.bounds_for_all_nodes();
        var position = this.canvas_container.position();
        var parent = this.canvas_container.parent();
        // Determine amount we need to expand on top/left
        var xmin_delta = fix_delta( bounds.xmin, 100 );
        var ymin_delta = fix_delta( bounds.ymin, 100 );
        // May need to expand farther to fill viewport
        xmin_delta = Math.max( xmin_delta, position.left );
        ymin_delta = Math.max( ymin_delta, position.top );
        var left = position.left - xmin_delta;
        var top = position.top - ymin_delta;
        // Same for width/height
        var width = round_up( bounds.xmax + 100, 100 ) + xmin_delta;
        var height = round_up( bounds.ymax + 100, 100 ) + ymin_delta;
        width = Math.max( width, - left + parent.width() );
        height = Math.max( height, - top + parent.height() );
        // Grow the canvas container
        this.canvas_container.css( {
            left: left,
            top: top,
            width: width,
            height: height
        });
        // Move elements back if needed
        this.canvas_container.children().each( function() {
            var p = $(this).position();
            $(this).css( "left", p.left + xmin_delta );
            $(this).css( "top", p.top + ymin_delta );
        });
    }
});

function fix_delta( x, n ) {
    if ( x < n|| x > 3*n ) {
        new_pos = ( Math.ceil( ( ( x % n ) ) / n ) + 1 ) * n;
        return ( - ( x - new_pos ) );
    }
    return 0;
}
    
function round_up( x, n ) {
    return Math.ceil( x / n ) * n;
}
     
function prebuild_node( type, title_text, tool_id ) {
    var f = $("<div class='toolForm toolFormInCanvas'></div>");
    var node = new Node( f );
    node.type = type;
    if ( type == 'tool' ) {
        node.tool_id = tool_id;
    }
    var title = $("<div class='toolFormTitle unselectable'>" + title_text + "</div>" );
    f.append( title );
    f.css( "left", $(window).scrollLeft() + 20 ); f.css( "top", $(window).scrollTop() + 20 );    
    var b = $("<div class='toolFormBody'></div>");
    var tmp = "<div><img height='16' align='middle' src='" + galaxy_config.root + "static/images/loading_small_white_bg.gif'/> loading tool info...</div>";
    b.append( tmp );
    node.form_html = tmp;
    f.append( b );
    // Fix width to computed width
    // Now add floats
    var buttons = $("<div class='buttons' style='float: right;'></div>");
    buttons.append( $("<div>").addClass("fa-icon-button fa fa-times").click( function( e ) {
        node.destroy();
    }));
    // Place inside container
    f.appendTo( "#canvas-container" );
    // Position in container
    var o = $("#canvas-container").position();
    var p = $("#canvas-container").parent();
    var width = f.width();
    var height = f.height();
    f.css( { left: ( - o.left ) + ( p.width() / 2 ) - ( width / 2 ), top: ( - o.top ) + ( p.height() / 2 ) - ( height / 2 ) } );
    buttons.prependTo( title );
    width += ( buttons.width() + 10 );
    f.css( "width", width );
    $(f).bind( "dragstart", function() {
        workflow.activate_node( node );
    }).bind( "dragend", function() {
        workflow.node_changed( this );
        workflow.fit_canvas_to_nodes();
        canvas_manager.draw_overview();
    }).bind( "dragclickonly", function() {
       workflow.activate_node( node ); 
    }).bind( "drag", function( e, d ) {
        // Move
        var po = $(this).offsetParent().offset(),
            x = d.offsetX - po.left,
            y = d.offsetY - po.top;
        $(this).css( { left: x, top: y } );
        // Redraw
        $(this).find( ".terminal" ).each( function() {
            this.terminal.redraw();
        });
    });
    return node;
}

function add_node( type, title_text, tool_id ) {
    // Abstraction for use by galaxy.workflow.js to hide
    // some editor details from workflow code and reduce duplication
    // between add_node_for_tool and add_node_for_module.
    var node = prebuild_node( type, title_text, tool_id );
    workflow.add_node( node );
    workflow.fit_canvas_to_nodes();
    canvas_manager.draw_overview();
    workflow.activate_node( node );    
    return node;
}


var ext_to_type = null;
var type_to_type = null;

function issubtype( child, parent ) {
    child = ext_to_type[child];
    parent = ext_to_type[parent];
    return ( type_to_type[child] ) && ( parent in type_to_type[child] );
}

function populate_datatype_info( data ) {
    ext_to_type = data.ext_to_class_name;
    type_to_type = data.class_to_classes;
}

// FIXME: merge scroll panel into CanvasManager, clean up hardcoded stuff.

function ScrollPanel( panel ) {
    this.panel = panel;
}
$.extend( ScrollPanel.prototype, {
    test: function( e, onmove ) {
        clearTimeout( this.timeout );
        var x = e.pageX,
            y = e.pageY,
            // Panel size and position
            panel = $(this.panel),
            panel_pos = panel.position(),
            panel_w = panel.width(),
            panel_h = panel.height(),
            // Viewport size and offset
            viewport = panel.parent(),
            viewport_w = viewport.width(),
            viewport_h = viewport.height(),
            viewport_offset = viewport.offset(),
            // Edges of viewport (in page coordinates)
            min_x = viewport_offset.left,
            min_y = viewport_offset.top,
            max_x = min_x + viewport.width(),
            max_y = min_y + viewport.height(),
            // Legal panel range
            p_min_x = - ( panel_w - ( viewport_w / 2 ) ),
            p_min_y = - ( panel_h - ( viewport_h / 2 )),
            p_max_x = ( viewport_w / 2 ),
            p_max_y = ( viewport_h / 2 ),
            // Did the panel move?
            moved = false,
            // Constants
            close_dist = 5,
            nudge = 23;
        if ( x - close_dist < min_x ) {
            if ( panel_pos.left < p_max_x ) {
                var t = Math.min( nudge, p_max_x - panel_pos.left );
                panel.css( "left", panel_pos.left + t );
                moved = true;
            }
        } else if ( x + close_dist > max_x ) {
            if ( panel_pos.left > p_min_x ) {
                var t = Math.min( nudge, panel_pos.left  - p_min_x );
                panel.css( "left", panel_pos.left - t );
                moved = true;
            }
        } else if ( y - close_dist < min_y ) {
            if ( panel_pos.top < p_max_y ) {
                var t = Math.min( nudge, p_max_y - panel_pos.top );
                panel.css( "top", panel_pos.top + t );
                moved = true;
            }
        } else if ( y + close_dist > max_y ) {
            if ( panel_pos.top > p_min_y ) {
                var t = Math.min( nudge, panel_pos.top  - p_min_x );
                panel.css( "top", ( panel_pos.top - t ) + "px" );
                moved = true;
            }
        }
        if ( moved ) {
            // Keep moving even if mouse doesn't move
            onmove();
            var panel = this;
            this.timeout = setTimeout( function() { panel.test( e, onmove ); }, 50 );
        }
    },
    stop: function( e, ui ) {
        clearTimeout( this.timeout );
    }
});

function CanvasManager( canvas_viewport, overview ) {
    this.cv = canvas_viewport;
    this.cc = this.cv.find( "#canvas-container" );
    this.oc = overview.find( "#overview-canvas" );
    this.ov = overview.find( "#overview-viewport" );
    // Make overview box draggable
    this.init_drag();
}
$.extend( CanvasManager.prototype, {
    init_drag : function () {
        var self = this;
        var move = function( x, y ) {
            x = Math.min( x, self.cv.width() / 2 );
            x = Math.max( x, - self.cc.width() + self.cv.width() / 2 );
            y = Math.min( y, self.cv.height() / 2 );
            y = Math.max( y, - self.cc.height() + self.cv.height() / 2 );
            self.cc.css( {
                left: x,
                top: y
            });
            self.update_viewport_overlay();
        };
        // Dragging within canvas background
        this.cc.each( function() {
            this.scroll_panel = new ScrollPanel( this );
        });
        var x_adjust, y_adjust;
        this.cv.bind( "dragstart", function() {
            var o = $(this).offset();
            var p = self.cc.position();
            y_adjust = p.top - o.top;
            x_adjust = p.left - o.left;
        }).bind( "drag", function( e, d ) {
            move( d.offsetX + x_adjust, d.offsetY + y_adjust );
        }).bind( "dragend", function() {
            workflow.fit_canvas_to_nodes();
            self.draw_overview();
        });
        // Dragging for overview pane
        this.ov.bind( "drag", function( e, d ) {
            var in_w = self.cc.width(),
                in_h = self.cc.height(),
                o_w = self.oc.width(),
                o_h = self.oc.height(),
                p = $(this).offsetParent().offset(),
                new_x_offset = d.offsetX - p.left,
                new_y_offset = d.offsetY - p.top;
            move( - ( new_x_offset / o_w * in_w ),
                  - ( new_y_offset / o_h * in_h ) );
        }).bind( "dragend", function() {
            workflow.fit_canvas_to_nodes();
            self.draw_overview();
        });
        // Dragging for overview border (resize)
        $("#overview-border").bind( "drag", function( e, d ) {
            var op = $(this).offsetParent();
            var opo = op.offset();
            var new_size = Math.max( op.width() - ( d.offsetX - opo.left ),
                                     op.height() - ( d.offsetY - opo.top ) );
            $(this).css( {
                width: new_size,
                height: new_size
            });
            self.draw_overview();
        });
        
        /*  Disable dragging for child element of the panel so that resizing can
            only be done by dragging the borders */
        $("#overview-border div").bind("drag", function() { });
        
    },
    update_viewport_overlay: function() {
        var cc = this.cc,
            cv = this.cv,
            oc = this.oc,
            ov = this.ov,
            in_w = cc.width(),
            in_h = cc.height(),
            o_w = oc.width(),
            o_h = oc.height(),
            cc_pos = cc.position();        
        ov.css( {
            left: - ( cc_pos.left / in_w * o_w ),
            top: - ( cc_pos.top / in_h * o_h ),
            // Subtract 2 to account for borders (maybe just change box sizing style instead?)
            width: ( cv.width() / in_w * o_w ) - 2,
            height: ( cv.height() / in_h * o_h ) - 2
        });
    },
    draw_overview: function() {
        var canvas_el = $("#overview-canvas"),
            size = canvas_el.parent().parent().width(),
            c = canvas_el.get(0).getContext("2d"),
            in_w = $("#canvas-container").width(),
            in_h = $("#canvas-container").height();
        var o_h, shift_h, o_w, shift_w;
        // Fit canvas into overview area
        var cv_w = this.cv.width();
        var cv_h = this.cv.height();
        if ( in_w < cv_w && in_h < cv_h ) {
            // Canvas is smaller than viewport
            o_w = in_w / cv_w * size;
            shift_w = ( size - o_w ) / 2;
            o_h = in_h / cv_h * size;
            shift_h = ( size - o_h ) / 2;
        } else if ( in_w < in_h ) {
            // Taller than wide
            shift_h = 0;
            o_h = size;
            o_w = Math.ceil( o_h * in_w / in_h );
            shift_w = ( size - o_w ) / 2;
        } else {
            // Wider than tall
            o_w = size;
            shift_w = 0;
            o_h = Math.ceil( o_w * in_h / in_w );
            shift_h = ( size - o_h ) / 2;
        }
        canvas_el.parent().css( {
           left: shift_w,
           top: shift_h,
           width: o_w,
           height: o_h
        });
        canvas_el.attr( "width", o_w );
        canvas_el.attr( "height", o_h );
        // Draw overview
        $.each( workflow.nodes, function( id, node ) {
            c.fillStyle = "#D2C099";
            c.strokeStyle = "#D8B365";
            c.lineWidth = 1;
            var node_element = $(node.element),
                position = node_element.position(),
                x = position.left / in_w * o_w,
                y = position.top / in_h * o_h,
                w = node_element.width() / in_w * o_w,
                h = node_element.height() / in_h * o_h;
            if (node.tool_errors){
                c.fillStyle = "#FFCCCC";
                c.strokeStyle = "#AA6666";
            } else if (node.workflow_outputs != undefined && node.workflow_outputs.length > 0){
                c.fillStyle = "#E8A92D";
                c.strokeStyle = "#E8A92D";
            }
            c.fillRect( x, y, w, h );
            c.strokeRect( x, y, w, h );
        });
        this.update_viewport_overlay();
    }
});



/**

Ditched Code...


    mapped_over_input_terminals: function() {
        var mapped_input_terminals = [];
        _.each( this.node.input_terminals, function( t ) {
            var mapOver = t.mapOver();
            if( mapOver.is_collection ) {
                mapped_input_terminals.push( t );
            }
        } );
        return mapped_input_terminals;
    },

**/
