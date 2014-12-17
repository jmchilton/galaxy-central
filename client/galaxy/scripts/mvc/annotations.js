define([
    "mvc/base-mvc",
    "utils/localization"
], function( baseMVC, _l ){
// =============================================================================
/** A view on any model that has a 'annotation' attribute
 */
var AnnotationEditor = Backbone.View
        .extend( baseMVC.LoggableMixin )
        .extend( baseMVC.HiddenUntilActivatedViewMixin ).extend({

    tagName     : 'div',
    className   : 'annotation-display',

    /** Set up listeners, parse options */
    initialize : function( options ){
        options = options || {};
        this.tooltipConfig = options.tooltipConfig || { placement: 'bottom' };
        //console.debug( this, options );
        // only listen to the model only for changes to annotations
        this.listenTo( this.model, 'change:annotation', function(){
            this.render();
        });
        this.hiddenUntilActivated( options.$activator, options );
    },

    /** Build the DOM elements, call select to on the created input, and set up behaviors */
    render : function(){
        var view = this;
        this.$el.html( this._template() );
        this.$el.find( "[title]" ).tooltip( this.tooltipConfig );

        //TODO: handle empties better
        this.$annotation().make_text_editable({
            use_textarea: true,
            on_finish: function( newAnnotation ){
                view.$annotation().text( newAnnotation );
                view.model.save({ annotation: newAnnotation }, { silent: true })
                    .fail( function(){
                        view.$annotation().text( view.model.previous( 'annotation' ) );
                    });
            }
        });
        return this;
    },

    /** @returns {String} the html text used to build the view's DOM */
    _template : function(){
        var annotation = this.model.get( 'annotation' );
        //if( !annotation ){
        //    //annotation = [ '<em class="annotation-empty">', _l( 'Click to add an annotation' ), '</em>' ].join( '' );
        //    annotation = [ '<em class="annotation-empty"></em>' ].join( '' );
        //}
        return [
            //TODO: make prompt optional
            '<label class="prompt">', _l( 'Annotation' ), '</label>',
            // set up initial tags by adding as CSV to input vals (necc. to init select2)
            '<div class="annotation" title="', _l( 'Edit annotation' ), '">',
                _.escape( annotation ),
            '</div>'
        ].join( '' );
    },

    /** @returns {jQuery} the main element for this view */
    $annotation : function(){
        return this.$el.find( '.annotation' );
    },

    /** shut down event listeners and remove this view's DOM */
    remove : function(){
        this.$annotation.off();
        this.stopListening( this.model );
        Backbone.View.prototype.remove.call( this );
    },

    /** string rep */
    toString : function(){ return [ 'AnnotationEditor(', this.model + '', ')' ].join(''); }
});
// =============================================================================
return {
    AnnotationEditor : AnnotationEditor
};
});
