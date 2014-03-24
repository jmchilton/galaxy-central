// dependencies
define([ "libs/underscore", "mvc/tools" ], function( _, Tools ) {

    var checkUncheckAll = function( name, check ) {
        $("input[name='" + name + "'][type='checkbox']").attr('checked', !!check);
    }

    // Inserts the Select All / Unselect All buttons for checkboxes
    $("div.checkUncheckAllPlaceholder").each( function() {
        var check_name = $(this).attr("checkbox_name");
        select_link = $("<a class='action-button'></a>").text("Select All").click(function() {
           checkUncheckAll(check_name, true);
        });
        unselect_link = $("<a class='action-button'></a>").text("Unselect All").click(function() {
           checkUncheckAll(check_name, false);
        });
        $(this).append(select_link).append(" ").append(unselect_link);
    });

    var SELECTION_TYPE = {
        'select_single': {
            'icon_class': 'fa-file-o',
            'select_by': 'Run tool on single input',
            'allow_remap': true
        },
        'select_multiple': {
            'icon_class': 'fa-files-o',
            'select_by': 'Run tool in parallel across multiple datasets',
            'allow_remap': false
        },
        'select_collection': { // NOT YET IMPLEMENTED
            'icon_class': 'fa-folder-o',
            'select_by': 'Run tool in parallel across dataset collection',
            'allow_remap': false
        },
        'multiselect_single': {
            'icon_class': 'fa-list-alt',
            'select_by': 'Run tool over multiple datasets',
            'allow_remap': true
        },
        'multiselect_collection': {
            'icon_class': 'fa-folder-o',
            'select_by': 'Run tool over dataset collection',
            'allow_remap': false,
        },
        'select_single_collection': {
            'icon_class': 'fa-file-o',
            'select_by': 'Run tool on single collection',
            'allow_remap': true
        },
        'select_map_over_collections': {
            'icon_class': 'fa-folder-o',
            'select_by': 'Map tool over compontents of nested collection',
            'allow_remap': false,            
        }
    };

    var SwitchSelectView = Backbone.View.extend({
        initialize: function( data ) {
            var default_option = data.default_option;
            var default_index = null;
            this.switchOptions = data.switch_options;
            this.prefix = data.prefix;
            var el = this.$el;
            var view = this;

            var index = 0;
            _.each( this.switchOptions, function( option, on_value ) {
                var selection_type = SELECTION_TYPE[on_value];
                var iIndex = index++;
                if( default_option == on_value ) {
                    default_index = iIndex;
                }
                var button = $('<i class="fa ' + selection_type['icon_class'] + '" style="padding-left: 5px; padding-right: 2px;"></i>').click(function() {
                    view.enableSelectBy( iIndex, on_value );
                }).attr(
                    'title',
                    selection_type['select_by']
                );
                view.formRow().find( "label" ).append( button );
            });
            if( default_index != null) {
                view.enableSelectBy( default_index, default_option );
            }
        },

        formRow: function() {
            return this.$el.closest( ".form-row" );
        },

        render: function() {
        },

        enableSelectBy: function( enableIndex, on_value ) {
            var el = this.$el;
            var selection_type = SELECTION_TYPE[on_value];
            if(selection_type["allow_remap"]) {
                $("div#remap-row").css("display", "none");
            } else {
                $("div#remap-row").css("display", "inherit");
            }
            this.formRow().find( "i" ).each(function(index, iElement) {
                if(index == enableIndex) {
                    $(iElement).css('color', 'black');
                } else {
                    $(iElement).css('color', 'Gray');
                }
            });
            var select = el.find( "select" );
            var options = this.switchOptions[ on_value ]
            select.attr( "name", this.prefix + options.name );
            select.attr( "multiple", options.multiple );
            select.html(""); // clear out select list
            _.each( options.options, function( option ) {
                var text = option[0];
                var value = option[1];
                var selected = option[2];
                select.append($("<option />", {text: text, val: value, selected: selected}));
            });
        }
    });

    return {
        SwitchSelectView: SwitchSelectView
    };

});
