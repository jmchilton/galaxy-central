define([
    "mvc/dataset/hda-model",
    "mvc/dataset/hda-base"
], function( hdaModel, hdaBase ){
/* global Backbone, LoggableMixin */
//==============================================================================
/** @class Read only view for HistoryDatasetCollectionAssociation.
 *  @name HDABaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DatasetCollectionBaseView = hdaBase.HistoryContentBaseView.extend({
    className   : "dataset hda history-panel-hda",
    id          : function(){ return 'hdca-' + this.model.get( 'id' ); },

    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( this + '.initialize:', attributes );
    },

    render : function( fade ){
        var $newRender = this._buildNewRender();

        this._queueNewRender( $newRender, fade );
        return this;
    },
    
    _buildNewRender : function(){
        var $newRender = $( _.template(this.templateSkeleton(), this.model.toJSON() ) );
        // TODO: Fill out rest of this...
        // $newRender.find( '.dataset-primary-actions' ).append( this._render_titleButtons() );
        // $newRender.children( '.dataset-body' ).replaceWith( this._render_body() );
        // this._setUpBehaviors( $newRender );
        return $newRender;
    },

    // These are non-ops for now, some operations would apply - some wouldn't,
    // should resolve that before making these do something.
    showSelector : function() {},
    hideSelector : function() {},

    // main template for folder browsing
    templateSkeleton : function (){
        var tmpl_array = [
        '<div class="dataset hda">',
        '    <div class="dataset-warnings">',
        '<% if ( deleted ) { %>',
        '        <div class="dataset-deleted-msg warningmessagesmall"><strong>',
        '             This dataset has been deleted.', // Localize?
        '        </div>',
        '<% } %>',
        '<% if ( ! visible ) { %>',
        '        <div class="dataset-hidden-msg warningmessagesmall"><strong>',
        '             This dataset has been hidden.', // Localize?
        '        </div>',
        '<% } %>',
        '     </div>',
        '     <div class="dataset-selector"><span class="fa fa-2x fa-square-o"></span></div>',
        '         <div class="dataset-primary-actions"></div>',
        '         <div class="dataset-title-bar clear" tabindex="0">',
        '              <span class="dataset-state-icon state-icon"></span>',
        '              <div class="dataset-title">',
        '                   <span class="hda-hid"><%= hid %></span>',
        '                   <span class="dataset-name"><%= name %></span>',
        '              </div>',
        '     </div>',
        '     <div class="dataset-body"></div>',
        '</div>',
        ];
        return tmpl_array.join('');
    },

    templateBody : function() {

    }

});

//==============================================================================
return {
    DatasetCollectionBaseView : DatasetCollectionBaseView
};

});