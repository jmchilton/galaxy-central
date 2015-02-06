// dependencies
define(['utils/utils', 'mvc/ui/ui-table', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc'], function(Utils, Table, Portlet, Ui) {

/** This class creates a ui component which enables the dynamic creation of portlets
*/
var View = Backbone.View.extend({
    // default options
    optionsDefault : {
        max : null
    },

    /** Initialize
    */
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement('<div/>');
        
        // link this
        var self = this;
        
        // create button
        this.button_new = new Ui.ButtonIcon({
            icon    : 'fa-plus',
            title   : 'Insert ' + options.title_new,
            tooltip : 'Add new ' + options.title_new + ' block',
            floating: 'clear',
            onclick : function() {
                if (options.onnew) {
                    options.onnew();
                }
            }
        });
        
        // create table
        this.table = new Table.View({
            cls     : 'ui-table-plain',
            content : ''
        });
        
        // append button
        this.$el.append(this.table.$el);
        
        // add button
        this.$el.append($('<div/>').append(this.button_new.$el));
        
        // clear list
        this.list = {};
    },
    
    /** Number of repeat blocks
    */
    size: function() {
        return _.size(this.list);
    },
    
    /** Add new repeat block
    */
    add: function(options) {
        // delete button
        var button_delete = new Ui.ButtonIcon({
            icon    : 'fa-trash-o',
            tooltip : 'Delete this repeat block',
            cls     : 'ui-button-icon-plain',
            onclick : function() {
                if (options.ondel) {
                    options.ondel();
                }
            }
        });
        
        // create portlet
        var portlet = new Portlet.View({
            id              : options.id,
            title           : '<b>' + options.title + '</b>',
            cls             : 'ui-portlet-repeat',
            operations      : {
                button_delete : button_delete
            }
        });
        
        // hide button
        if (!options.ondel) {
            button_delete.remove();
        }
        
        // append content
        portlet.append(options.$el);
        
        // tag as section row
        portlet.$el.addClass('section-row');
        
        // append to dom
        this.list[options.id] = portlet;
        
        // append to dom
        this.table.add(portlet.$el);
        this.table.append('row_' + options.id, true);
        
        // validate maximum
        if (this.options.max > 0 && this.size() >= this.options.max) {
            this.button_new.disable();
        }
    },
    
    /** Delete repeat block
    */
    del: function(id) {
        if (this.list[id]) {
            // delete table row
            var table_row = this.table.get('row_' + id);
            table_row.remove();
            
            // remove from list
            delete this.list[id];
            
            // enable new button
            this.button_new.enable();
        }
    },
    
    /** Retitle/Enumerate repeat blocks
    */
    retitle: function(new_title) {
        var index = 0;
        for (var id in this.list) {
            this.list[id].title(++index + ': ' + new_title);
        }
    }
});

return {
    View : View
}

});
