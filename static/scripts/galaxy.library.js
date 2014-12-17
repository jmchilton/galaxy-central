// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === MAIN GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

define([
    "galaxy.masthead",
    "utils/utils",
    "libs/toastr",
    "mvc/base-mvc",
    "mvc/library/library-model",
    "mvc/library/library-folderlist-view",
    "mvc/library/library-librarylist-view",
    "mvc/library/library-librarytoolbar-view",
    "mvc/library/library-foldertoolbar-view",
    "mvc/library/library-dataset-view",
    "mvc/library/library-library-view",
    "mvc/library/library-folder-view"
    ],
    function(mod_masthead,
       mod_utils,
       mod_toastr,
       mod_baseMVC,
       mod_library_model,
       mod_folderlist_view,
       mod_librarylist_view,
       mod_librarytoolbar_view,
       mod_foldertoolbar_view,
       mod_library_dataset_view,
       mod_library_library_view,
       mod_library_folder_view
       ) {

// ============================================================================
// ROUTER
var LibraryRouter = Backbone.Router.extend({
  initialize: function() {
    this.routesHit = 0;
    //keep count of number of routes handled by the application
    Backbone.history.on( 'route', function() { this.routesHit++; }, this );
},

routes: {
    ""                                                              : "libraries",
    "page/:show_page"                                               : "libraries_page",
    "library/:library_id/permissions"                               : "library_permissions",
    "folders/:folder_id/permissions"                                : "folder_permissions",
    "folders/:id"                                                   : "folder_content",
    "folders/:id/page/:show_page"                                   : "folder_page",
    "folders/:folder_id/datasets/:dataset_id"                       : "dataset_detail",
    "folders/:folder_id/datasets/:dataset_id/permissions"           : "dataset_permissions",
    "folders/:folder_id/datasets/:dataset_id/versions/:ldda_id"     : "dataset_version",
    "folders/:folder_id/download/:format"                           : "download",
    "folders/:folder_id/import/:source"                             : "import_datasets"
},

back: function() {
    if( this.routesHit > 1 ) {
      //more than one route hit -> user did not land to current page directly
      window.history.back();
  } else {
      //otherwise go to the home page. Use replaceState if available so
      //the navigation doesn't create an extra history entry
      this.navigate( '#', { trigger:true, replace:true } );
  }
}
});

// ============================================================================
/** session storage for library preferences */
var LibraryPrefs = mod_baseMVC.SessionStorageModel.extend({
    defaults : {
        with_deleted      : false,
        sort_order        : 'asc',
        sort_by           : 'name',
        library_page_size : 20,
        folder_page_size  : 15
    }
});

// ============================================================================
// Main controller of Galaxy Library
var GalaxyLibrary = Backbone.View.extend({

    libraryToolbarView: null,
    libraryListView: null,
    library_router: null,
    libraryView: null,
    folderToolbarView: null,
    folderListView: null,
    datasetView: null,

    initialize : function(){
        Galaxy.libraries = this;

        this.preferences = new LibraryPrefs( { id: 'global-lib-prefs' } );

        this.library_router = new LibraryRouter();

        this.library_router.on( 'route:libraries', function() {
            Galaxy.libraries.libraryToolbarView = new mod_librarytoolbar_view.LibraryToolbarView();
            Galaxy.libraries.libraryListView = new mod_librarylist_view.LibraryListView();
        });
        
        this.library_router.on('route:libraries_page', function( show_page ) {
            if ( Galaxy.libraries.libraryToolbarView === null ){
                Galaxy.libraries.libraryToolbarView = new mod_librarytoolbar_view.LibraryToolbarView();
                Galaxy.libraries.libraryListView = new mod_librarylist_view.LibraryListView( { show_page: show_page } );
            } else {
                Galaxy.libraries.libraryListView.render( { show_page: show_page } )
            }
        });

        this.library_router.on( 'route:folder_content', function( id ) {
            if (Galaxy.libraries.folderToolbarView){ 
                Galaxy.libraries.folderToolbarView.$el.unbind( 'click' );
            }
            Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView( { id: id } );
            Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView( { id: id } );
        });

        this.library_router.on( 'route:folder_page', function( id, show_page ) {
            if ( Galaxy.libraries.folderToolbarView === null ){
                Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView( {id: id} );
                Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView( { id: id, show_page: show_page } );
            } else {
                Galaxy.libraries.folderListView.render( { id: id, show_page: parseInt( show_page ) } )
            }
        });

        this.library_router.on( 'route:download', function( folder_id, format ) {
            if ( $( '#folder_list_body' ).find( ':checked' ).length === 0 ) {
                mod_toastr.info( 'You must select at least one dataset to download' );
                Galaxy.libraries.library_router.navigate( 'folders/' + folder_id, { trigger: true, replace: true } );
            } else {
                Galaxy.libraries.folderToolbarView.download( folder_id, format );
                Galaxy.libraries.library_router.navigate( 'folders/' + folder_id, { trigger: false, replace: true } );
            }
        });

        this.library_router.on( 'route:dataset_detail', function(folder_id, dataset_id){
            if (Galaxy.libraries.datasetView){
                Galaxy.libraries.datasetView.$el.unbind('click');
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({id: dataset_id});
        });

        this.library_router.on( 'route:dataset_version', function(folder_id, dataset_id, ldda_id){
            if (Galaxy.libraries.datasetView){
                Galaxy.libraries.datasetView.$el.unbind('click');
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({id: dataset_id, ldda_id: ldda_id, show_version: true});
        });

        this.library_router.on( 'route:dataset_permissions', function(folder_id, dataset_id){
            if (Galaxy.libraries.datasetView){
                Galaxy.libraries.datasetView.$el.unbind('click');
            }
            Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({id: dataset_id, show_permissions: true});
        });

        this.library_router.on( 'route:library_permissions', function(library_id){
            if (Galaxy.libraries.libraryView){
                Galaxy.libraries.libraryView.$el.unbind('click');
            }
            Galaxy.libraries.libraryView = new mod_library_library_view.LibraryView({id: library_id, show_permissions: true});
        });

        this.library_router.on( 'route:folder_permissions', function(folder_id){
            if (Galaxy.libraries.folderView){
                Galaxy.libraries.folderView.$el.unbind('click');
            }
            Galaxy.libraries.folderView = new mod_library_folder_view.FolderView({id: folder_id, show_permissions: true});
        });

        this.library_router.on( 'route:import_datasets', function( folder_id, source ){
            if ( Galaxy.libraries.folderToolbarView && Galaxy.libraries.folderListView ){
                Galaxy.libraries.folderToolbarView.showImportModal( { source:source } );
            } else {
                Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView( { id: folder_id } );
                Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView( { id: folder_id } );
                Galaxy.libraries.folderToolbarView.showImportModal( { source: source } );
            }
        });

        Backbone.history.start({pushState: false});
    }
});

return {
    GalaxyApp: GalaxyLibrary
};

});
