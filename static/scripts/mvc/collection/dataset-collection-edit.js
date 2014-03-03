define([
    "mvc/collection/dataset-collection-base",
], function( datasetCollectionBase ){
//==============================================================================
/** @class Editing view for HistoryDatasetCollectionAssociation.
 *  @name HDABaseView
 *
 *  @augments DatasetCollectionBaseView
 *  @constructs
 */
var DatasetCollectionEditView = datasetCollectionBase.DatasetCollectionBaseView.extend( {

    initialize  : function( attributes ){
        datasetCollectionBase.DatasetCollectionBaseView.prototype.initialize.call( this, attributes );
    },

});

//==============================================================================
return {
    DatasetCollectionEditView  : DatasetCollectionEditView
};

});