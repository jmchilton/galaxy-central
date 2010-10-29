// IE doesn't implement Array.indexOf
if (!Array.indexOf) {
    Array.prototype.indexOf = function(obj) {
        for (var i = 0, len = this.length; i < len; i++) {
            if (this[i] == obj) {
                return i;
            }
        }
        return -1;
    }
}

// Returns the number of keys (elements) in an array/dictionary.
function obj_length(obj) {
    if (obj.length !== undefined) {
        return obj.length;
    }

    var count = 0;
    for (var element in obj) {
        count++;
    }
    return count;
}

$.fn.makeAbsolute = function(rebase) {
    return this.each(function() {
        var el = $(this);
        var pos = el.position();
        el.css({
            position: "absolute",
            marginLeft: 0, marginTop: 0,
            top: pos.top, left: pos.left,
            right: $(window).width() - ( pos.left + el.width() )
        });
        if (rebase) {
            el.remove().appendTo("body");
        }
    });
};

function ensure_popup_helper() {
    // And the helper below the popup menus
    if ( $( "#popup-helper" ).length === 0 ) {
        $( "<div id='popup-helper'/>" ).css( {
            background: 'white', opacity: 0, zIndex: 15000,
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' 
        } ).appendTo( "body" ).hide();
    }
}

function attach_popupmenu( button_element, wrapper ) {
    var clean = function() {
        wrapper.unbind().hide();
        $("#popup-helper").unbind( "click.popupmenu" ).hide();
        // $(document).unbind( "click.popupmenu" ); 
    };
    var click_handler = function( e ) {
        // var o = $(button_element).offset();
        $("#popup-helper").bind( "click.popupmenu", clean ).show();
        // $(document).bind( "click.popupmenu", clean );
        // Show off screen to get size right
        wrapper.click( clean ).css( { left: 0, top: -1000 } ).show();
        // console.log( e.pageX, $(document).scrollLeft() + $(window).width(), $(menu_element).width() );
        var x = e.pageX - wrapper.width() / 2 ;
        x = Math.min( x, $(document).scrollLeft() + $(window).width() - $(wrapper).width() - 20 );
        x = Math.max( x, $(document).scrollLeft() + 20 );
        // console.log( e.pageX, $(document).scrollLeft() + $(window).width(), $(menu_element).width() );
        
        
        wrapper.css( {
            top: e.pageY - 5,
            left: x
        } );
        return false;
    };
    $(button_element).bind("click", click_handler);
}

function make_popupmenu( button_element, options ) {
    ensure_popup_helper();
    // var container_element = $(button_element);
    // if ( container_element.parent().hasClass( "combo-button" ) ) {
    //    container_element = container_element.parent();
    // }
    // container_element).css( "position", "relative" );
    var menu_element = $( "<ul id='" + button_element.attr('id') + "-menu'></ul>" );
    if (obj_length(options) <= 0) {
        $("<li/>").html("No options").appendTo(menu_element);
    }
    $.each( options, function( k, v ) {
        if (v) {
            $("<li/>").html(k).click(v).appendTo(menu_element);
        } else {
            $("<li class='head'/>").html(k).appendTo(menu_element);
        }
    });
    var wrapper = $( "<div class='popmenu-wrapper'>" );
    wrapper.append( menu_element )
           .append( "<div class='overlay-border'>" )
           .css( "position", "absolute" )
           .appendTo( "body" )
           .hide();
    attach_popupmenu( button_element, wrapper );
    return menu_element;
}

// Toggle popup menu options using regular expression on option names.
function show_hide_popupmenu_options( menu, option_name_re, show ) {
    var show = (show === undefined ? true : show );
    var re = new RegExp(option_name_re);
    $(menu).find("li").each( function() {
        if ( re.exec( $(this).text() ) )
            if (show)
                $(this).show();
            else
                $(this).hide();
    });
}

function make_popup_menus() {
    jQuery( "div[popupmenu]" ).each( function() {
        var options = {};
        $(this).find( "a" ).each( function() {
            var confirmtext = $(this).attr( "confirm" ),
                href = $(this).attr( "href" ),
                target = $(this).attr( "target" );
            options[ $(this).text() ] = function() {
                if ( !confirmtext || confirm( confirmtext ) ) {
                    var f = window;
                    if ( target == "_parent" ) {
                        f = window.parent;
                    } else if ( target == "_top" ) {
                        f = window.top;
                    }
                    f.location = href;
                }
            };
        });
        var b = $( "#" + $(this).attr( 'popupmenu' ) );
        b.find("a").bind("click", function(e) {
            e.stopPropagation(); // Stop bubbling so clicking on the link goes through
            return true;
        });
        make_popupmenu( b, options );
        $(this).remove();
        b.addClass( "popup" ).show();
    });
}

// Alphanumeric/natural sort fn
function naturalSort(a, b) {
    // setup temp-scope variables for comparison evauluation
    var re = /(-?[0-9\.]+)/g,
        x = a.toString().toLowerCase() || '',
        y = b.toString().toLowerCase() || '',
        nC = String.fromCharCode(0),
        xN = x.replace( re, nC + '$1' + nC ).split(nC),
        yN = y.replace( re, nC + '$1' + nC ).split(nC),
        xD = (new Date(x)).getTime(),
        yD = xD ? (new Date(y)).getTime() : null;
    // natural sorting of dates
    if ( yD )
        if ( xD < yD ) return -1;
        else if ( xD > yD ) return 1;
    // natural sorting through split numeric strings and default strings
    for( var cLoc = 0, numS = Math.max(xN.length, yN.length); cLoc < numS; cLoc++ ) {
        oFxNcL = parseFloat(xN[cLoc]) || xN[cLoc];
        oFyNcL = parseFloat(yN[cLoc]) || yN[cLoc];
        if (oFxNcL < oFyNcL) return -1;
        else if (oFxNcL > oFyNcL) return 1;
    }
    return 0;
}

// Replace select box with a text input box + autocomplete.
function replace_big_select_inputs(min_length, max_length) {
    // To do replace, jQuery's autocomplete plugin must be loaded.
    if (!jQuery().autocomplete)
        return;
    
    // Set default for min_length and max_length
    if (min_length === undefined)
        min_length = 20;
    if (max_length === undefined)
        max_length = 3000;
    
    $('select').each( function() {
        var select_elt = $(this);
        // Make sure that options is within range.
        var num_options = select_elt.find('option').length;
        if ( (num_options < min_length) || (num_options > max_length) ) {
            return;
        }
            
        // Skip multi-select because widget cannot handle multi-select.
        if (select_elt.attr('multiple') == true) {
            return;
        }
            
        if (select_elt.hasClass("no-autocomplete")) {
            return;
        }
        
        // Replace select with text + autocomplete.
        var start_value = select_elt.attr('value');
        
        // Set up text input + autocomplete element.
        var text_input_elt = $("<input type='text' class='text-and-autocomplete-select'></input>");
        text_input_elt.attr('size', 40);
        text_input_elt.attr('name', select_elt.attr('name'));
        text_input_elt.attr('id', select_elt.attr('id'));
        text_input_elt.click( function() {
            // Show all. Also provide note that load is happening since this can be slow.
            var cur_value = $(this).val();
            $(this).val('Loading...');
            $(this).showAllInCache();
            $(this).val(cur_value);
            $(this).select();
        });

        // Get options for select for autocomplete.
        var select_options = [];
        var select_mapping = {};
        select_elt.children('option').each( function() {
            // Get text, value for option.
            var text = $(this).text();
            var value = $(this).attr('value');

            // Set options and mapping. Mapping is (i) [from text to value] AND (ii) [from value to value]. This
            // enables a user to type the value directly rather than select the text that represents the value. 
            select_options.push( text );
            select_mapping[ text ] = value;
            select_mapping[ value ] = value;

            // If this is the start value, set value of input element.
            if ( value == start_value ) {
                text_input_elt.attr('value', text);
            }
        });
        
        // Set initial text if it's empty.
        if ( start_value == '' || start_value == '?') {
            text_input_elt.attr('value', 'Click to Search or Select');
        }
        
        // Sort dbkey options list only.
        if (select_elt.attr('name') == 'dbkey')
            select_options = select_options.sort(naturalSort);
        
        // Do autocomplete.
        var autocomplete_options = { selectFirst: false, autoFill: false, mustMatch: false, matchContains: true, max: max_length, minChars : 0, hideForLessThanMinChars : false };
        text_input_elt.autocomplete(select_options, autocomplete_options);

        // Replace select with text input.
        select_elt.replaceWith(text_input_elt);
        
        // Set trigger to replace text with value when element's form is submitted. If text doesn't correspond to value, default to start value.
        var submit_hook = function() {
            // Try to convert text to value.
            var cur_value = text_input_elt.attr('value');
            var new_value = select_mapping[cur_value];
            if (new_value !== null && new_value !== undefined) {
                text_input_elt.attr('value', new_value);
            } 
            else {
                // If there is a non-empty start value, use that; otherwise unknown.
                if (start_value != "") {
                    text_input_elt.attr('value', start_value);
                } else {
                    // This is needed to make the DB key work.
                    text_input_elt.attr('value', '?');
                }
            }
        };
        text_input_elt.parents('form').submit( function() { submit_hook(); } );
        
        // Add custom event so that other objects can execute name --> value conversion whenever they want.
        $(document).bind("convert_dbkeys", function() { submit_hook(); } );
        
        // If select is refresh on change, mirror this behavior.
        if (select_elt.attr('refresh_on_change') == 'true') {
            // Get refresh vals.
            var ref_on_change_vals = select_elt.attr('refresh_on_change_values'),
                last_selected_value = select_elt.attr("last_selected_value");
            if (ref_on_change_vals !== undefined)
                ref_on_change_vals = ref_on_change_vals.split(',');
            
            // Function that attempts to refresh based on the value in the text element.
            var try_refresh_fn = function() {
                // Get new value and see if it can be matched.
                var new_value = select_mapping[text_input_elt.attr('value')];
                if (last_selected_value !== new_value && new_value !== null && new_value !== undefined) {
                    if (ref_on_change_vals !== undefined && $.inArray(new_value, ref_on_change_vals) === -1 && $.inArray(last_selected_value, ref_on_change_vals) === -1) {
                        return;
                    }
                    text_input_elt.attr('value', new_value);
                    $(window).trigger("refresh_on_change");
                    text_input_elt.parents('form').submit();
                }
            };
            
            // Attempt refresh if (a) result event fired by autocomplete (indicating autocomplete occurred) or (b) on keyup (in which
            // case a user may have manually entered a value that needs to be refreshed).
            text_input_elt.bind("result", try_refresh_fn);
            text_input_elt.keyup( function(e) {
                if (e.keyCode === 13) { // Return key
                    try_refresh_fn();
                }
            });
            
            // Disable return key so that it does not submit the form automatically. This is done because element should behave like a 
            // select (enter = select), not text input (enter = submit form).
            text_input_elt.keydown( function(e) {
                if (e.keyCode === 13) { // Return key
                    return false;
                }
            });
        }
    });
}

// Edit and save text asynchronously.
function async_save_text(click_to_edit_elt, text_elt_id, save_url, text_parm_name, num_cols, use_textarea, num_rows, on_start, on_finish) {
    // Set defaults if necessary.
    if (num_cols === undefined) {
        num_cols = 30;
    }
    if (num_rows === undefined) {
        num_rows = 4;
    }
    
    // Set up input element.
    $("#" + click_to_edit_elt).live( "click", function() {
        // Check if this is already active
        if ( $("#renaming-active").length > 0) {
            return;
        }
        var text_elt = $("#" + text_elt_id),
            old_text = text_elt.text(),
            t;
            
        if (use_textarea) {
            t = $("<textarea></textarea>").attr({ rows: num_rows, cols: num_cols }).text( $.trim(old_text) );
        } else {
            t = $("<input type='text'></input>").attr({ value: $.trim(old_text), size: num_cols });
        }
        t.attr("id", "renaming-active");
        t.blur( function() {
            $(this).remove();
            text_elt.show();
            if (on_finish) {
                on_finish(t);
            }
        });
        t.keyup( function( e ) {
            if ( e.keyCode === 27 ) {
                // Escape key
                $(this).trigger( "blur" );
            } else if ( e.keyCode === 13 ) {
                // Enter key submits
                var ajax_data = {};
                ajax_data[text_parm_name] = $(this).val();
                $(this).trigger( "blur" );
                $.ajax({
                    url: save_url,
                    data: ajax_data,
                    error: function() { 
                        alert( "Text editing for elt " + text_elt_id + " failed" );
                        // TODO: call finish or no? For now, let's not because error occurred.
                    },
                    success: function(processed_text) {
                        // Set new text and call finish method.
                        if (processed_text != "")
                            text_elt.text(processed_text);
                        else
                            text_elt.html("<em>None</em>");
                        if (on_finish) {
                            on_finish(t);
                        }
                    }
                });
            }
        });
        
        if (on_start) {
            on_start(t);
        }
        // Replace text with input object and focus & select.
        text_elt.hide();
        t.insertAfter( text_elt );
        t.focus();
        t.select();
        
        return;
    });
}

function init_history_items(historywrapper, noinit, nochanges) {

    var action = function() {
        // Load saved state and show as necessary
        try {
            var stored = $.jStore.store("history_expand_state");
            if (stored) {
                for (var id in stored) {
                    $("#" + id + " div.historyItemBody" ).show();
                }
            }
        } catch(err) {
            // Something was wrong with values in storage, so clear storage
            $.jStore.remove("history_expand_state");
        }

        // If Mozilla, hide scrollbars in hidden items since they cause animation bugs
        if ( $.browser.mozilla ) {
            $( "div.historyItemBody" ).each( function() {
                if ( ! $(this).is( ":visible" ) ) $(this).find( "pre.peek" ).css( "overflow", "hidden" );
            })
        }
        
        historywrapper.each( function() {
            var id = this.id;
            var body = $(this).children( "div.historyItemBody" );
            var peek = body.find( "pre.peek" )
            $(this).find( ".historyItemTitleBar > .historyItemTitle" ).wrap( "<a href='javascript:void(0);'></a>" ).click( function() {
                if ( body.is(":visible") ) {
                    // Hiding stuff here
                    if ( $.browser.mozilla ) { peek.css( "overflow", "hidden" ); }
                    body.slideUp( "fast" );
                    
                    if (!nochanges) { // Ignore embedded item actions
                        // Save setting
                        var prefs = $.jStore.store("history_expand_state");
                        if (prefs) {
                            delete prefs[id];
                            $.jStore.store("history_expand_state", prefs);
                        }
                    }
                } else {
                    // Showing stuff here
                    body.slideDown( "fast", function() { 
                        if ( $.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });
                    
                    if (!nochanges) {
                        // Save setting
                        var prefs = $.jStore.store("history_expand_state");
                        if (prefs === undefined) { prefs = {}; }
                        prefs[id] = true;
                        $.jStore.store("history_expand_state", prefs);
                    }
                }
                return false;
            });
        });
        
        // Generate 'collapse all' link
        $("#top-links > a.toggle").click( function() {
            var prefs = $.jStore.store("history_expand_state");
            if (prefs === undefined) { prefs = {}; }
            $( "div.historyItemBody:visible" ).each( function() {
                if ( $.browser.mozilla ) {
                    $(this).find( "pre.peek" ).css( "overflow", "hidden" );
                }
                $(this).slideUp( "fast" );
                if (prefs) {
                    delete prefs[$(this).parent().attr("id")];
                }
            });
            $.jStore.store("history_expand_state", prefs);
        }).show();
    }
    
    if (noinit) {
        action();
    } else {
        // Load jStore for local storage
        $.jStore.init("galaxy"); // Auto-select best storage
        $.jStore.engineReady(function() {
            action();
        });
    }
}

function commatize( number ) {
    number += ''; // Convert to string
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(number)) {
        number = number.replace(rgx, '$1' + ',' + '$2');
    }
    return number;
}

// Reset tool search to start state.
function reset_tool_search( initValue ) {
    // Function may be called in top frame or in tool_menu_frame; 
    // in either case, get the tool menu frame.
    var tool_menu_frame = $("#galaxy_tools").contents();
    if (tool_menu_frame.length == 0) {
        tool_menu_frame = $(document);
    }
        
    // Remove classes that indicate searching is active.
    $(this).removeClass("search_active");
    tool_menu_frame.find(".toolTitle").removeClass("search_match");
    
    // Reset visibility of tools and labels.
    tool_menu_frame.find(".toolSectionBody").hide();
    tool_menu_frame.find(".toolTitle").show();
    tool_menu_frame.find(".toolPanelLabel").show();
    tool_menu_frame.find(".toolSectionWrapper").each( function() {
        if ($(this).attr('id') != 'recently_used_wrapper') {
            // Default action.
            $(this).show();
        } else if ($(this).hasClass("user_pref_visible")) {
            $(this).show();
        }
    });
    tool_menu_frame.find("#search-no-results").hide();
    
    // Reset search input.
    tool_menu_frame.find("#search-spinner").hide();
    if (initValue) {
        var search_input = tool_menu_frame.find("#tool-search-query");
        search_input.val("search tools");
        search_input.css("font-style", "italic");
    }
}

// Create GalaxyAsync object.
var GalaxyAsync = function(log_action) {
    this.url_dict = {};
    this.log_action = (log_action === undefined ? false : log_action);
}

GalaxyAsync.prototype.set_func_url = function( func_name, url ) {
    this.url_dict[func_name] = url;
};

// Set user preference asynchronously.
GalaxyAsync.prototype.set_user_pref = function( pref_name, pref_value ) {
    // Get URL.
    var url = this.url_dict[arguments.callee];
    if (url === undefined) { return false; }
    $.ajax({                   
        url: url,
        data: { "pref_name" : pref_name, "pref_value" : pref_value },
        error: function() { return false; },
        success: function() { return true; }                                           
    });
};

// Log user action asynchronously.
GalaxyAsync.prototype.log_user_action = function( action, context, params ) {
    if (!this.log_action) { return; }
        
    // Get URL.
    var url = this.url_dict[arguments.callee];
    if (url === undefined) { return false; }
    $.ajax({                   
        url: url,
        data: { "action" : action, "context" : context, "params" : params },
        error: function() { return false; },
        success: function() { return true; }                                           
    });
};

// Add to trackster browser functionality
$(".trackster-add").live("click", function() {
    var dataset = this,
        dataset_jquery = $(this);
    $.ajax({
        url: dataset_jquery.attr("data-url"),
        dataType: "html",
        error: function() { alert( "Could not add this dataset to browser." ); },
        success: function(table_html) {
            var parent = window.parent;
            parent.show_modal("Add to Browser:", table_html, {
                "Cancel": function() {
                    parent.hide_modal();
                },
                "Insert into selected": function() {
                    $(parent.document).find('input[name=id]:checked').each(function() {
                        var vis_id = $(this).val();
                        parent.location = dataset_jquery.attr("action-url") + "&id=" + vis_id;
                    });
                },
                "Insert into new browser": function() {
                    parent.location = dataset_jquery.attr("new-url");
                }
            });
        }
    });
});



$(document).ready( function() {
    $("select[refresh_on_change='true']").change( function() {
        var select_field = $(this),
            select_val = select_field.val(),
            refresh = false,
            ref_on_change_vals = select_field.attr("refresh_on_change_values");
        if (ref_on_change_vals) {
            ref_on_change_vals = ref_on_change_vals.split(',');
            var last_selected_value = select_field.attr("last_selected_value");
            if ($.inArray(select_val, ref_on_change_vals) === -1 && $.inArray(last_selected_value, ref_on_change_vals) === -1) {
                return;
            }
        }
        $(window).trigger("refresh_on_change");
        select_field.get(0).form.submit();
    });
    
    // Links with confirmation
    $( "a[confirm]" ).click( function() {
        return confirm( $(this).attr("confirm") );
    });
    // Tooltips
    if ( $.fn.tipsy ) {
        $(".tooltip").tipsy( { gravity: 's' } );
    }
    // Make popup menus.
    make_popup_menus();
    
    // Replace big selects.
    replace_big_select_inputs(20, 1500);
});
