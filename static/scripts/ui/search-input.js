// from: https://raw.githubusercontent.com/umdjs/umd/master/jqueryPlugin.js
// Uses AMD or browser globals to create a jQuery plugin.
(function (factory) {
    if (typeof define === 'function' && define.amd) {
        //TODO: So...this turns out to be an all or nothing thing. If I load jQuery in the define below, it will
        //  (of course) wipe the old jquery *and all the plugins loaded into it*. So the define below *is still
        //  relying on jquery being loaded globally* in order to preserve plugins.
        define([], factory);
    } else {
        // Browser globals
        factory(jQuery);
    }

}(function () {
    var _l = window._l || function( s ){ return s; };

    /** searchInput: (jQuery plugin)
     *      Creates a search input, a clear button, and loading indicator
     *      within the selected node.
     *
     *      When the user either presses return or enters some minimal number
     *      of characters, a callback is called. Pressing ESC when the input
     *      is focused will clear the input and call a separate callback.
     */
    function searchInput( parentNode, options ){
//TODO: consolidate with tool menu functionality, use there
        var KEYCODE_ESC     = 27,
            KEYCODE_RETURN  = 13,
            $parentNode     = $( parentNode ),
            firstSearch     = true,
            defaults = {
                initialVal      : '',
                name            : 'search',
                placeholder     : 'search',
                classes         : '',
                onclear         : function(){},
                onfirstsearch   : null,
                onsearch        : function( inputVal ){},
                minSearchLen    : 0,
                escWillClear    : true,
                oninit          : function(){}
            };

        // .................................................................... input rendering and events
        // visually clear the search, trigger an event, and call the callback
        function clearSearchInput( event ){
            var $input = $( this ).parent().children( 'input' );
            //console.debug( this, 'clear', $input );
            $input.focus().val( '' ).trigger( 'clear:searchInput' );
            options.onclear();
        }

        // search for searchTerms, trigger an event, call the appropo callback (based on whether this is the first)
        function search( event, searchTerms ){
            //console.debug( this, 'searching', searchTerms );
            //TODO: I don't think this is classic jq custom event form? search.searchInput?
            $( this ).trigger( 'search:searchInput', searchTerms );
            if( typeof options.onfirstsearch === 'function' && firstSearch ){
                firstSearch = false;
                options.onfirstsearch( searchTerms );
            } else {
                options.onsearch( searchTerms );
            }
        }

        // .................................................................... input rendering and events
        function inputTemplate(){
            // class search-query is bootstrap 2.3 style that now lives in base.less
            return [ '<input type="text" name="', options.name, '" placeholder="', options.placeholder, '" ',
                            'class="search-query ', options.classes, '" ', '/>' ].join( '' );
        }

        // the search input that responds to keyboard events and displays the search value
        function $input(){
            return $( inputTemplate() )
                // select all text on a focus
                .focus( function( event ){
                    $( this ).select();
                })
                // attach behaviors to esc, return if desired, search on some min len string
                .keyup( function( event ){
                    event.preventDefault();
                    event.stopPropagation();
//TODO: doesn't work
                    if( !$( this ).val() ){ $( this ).blur(); }

                    // esc key will clear if desired
                    if( event.which === KEYCODE_ESC && options.escWillClear ){
                        clearSearchInput.call( this, event );

                    } else {
                        var searchTerms = $( this ).val();
                        // return key or the search string len > minSearchLen (if not 0) triggers search
                        if( ( event.which === KEYCODE_RETURN )
                        ||  ( options.minSearchLen && searchTerms.length >= options.minSearchLen ) ){
                            search.call( this, event, searchTerms );
                        } else if( !searchTerms.length ){
                            clearSearchInput.call( this, event );
                        }
                    }
                })
                .on( 'change', function( event ){
                    search.call( this, event, $( this ).val() );
                })
                .val( options.initialVal );
        }

        // .................................................................... clear button rendering and events
        // a button for clearing the search bar, placed on the right hand side
        function $clearBtn(){
            return $([ '<span class="search-clear fa fa-times-circle" ',
                             'title="', _l( 'clear search (esc)' ), '"></span>' ].join('') )
            .tooltip({ placement: 'bottom' })
            .click( function( event ){
                clearSearchInput.call( this, event );
            });
        }

        // .................................................................... loadingIndicator rendering
        // a button for clearing the search bar, placed on the right hand side
        function $loadingIndicator(){
            return $([ '<span class="search-loading fa fa-spinner fa-spin" ',
                             'title="', _l( 'loading...' ), '"></span>' ].join('') )
                .hide().tooltip({ placement: 'bottom' });
        }

        // .................................................................... commands
        // visually swap the load, clear buttons
        function toggleLoadingIndicator(){
            $parentNode.find( '.search-loading' ).toggle();
            $parentNode.find( '.search-clear' ).toggle();
        }

        // .................................................................... init
        // string command (not constructor)
        if( jQuery.type( options ) === 'string' ){
            if( options === 'toggle-loading' ){
                toggleLoadingIndicator();
            }
            return $parentNode;
        }

        // initial render
        if( jQuery.type( options ) === 'object' ){
            options = jQuery.extend( true, {}, defaults, options );
        }
        //NOTE: prepended
        return $parentNode.addClass( 'search-input' ).prepend([ $input(), $clearBtn(), $loadingIndicator() ]);
    }

    // as jq plugin
    jQuery.fn.extend({
        searchInput : function $searchInput( options ){
            return this.each( function(){
                return searchInput( this, options );
            });
        }
    });
}));
