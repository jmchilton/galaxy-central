
define([
    "galaxy.masthead",
    "utils/utils",
    "mvc/admin/admin-view",
    ],
    function(
       mod_masthead,
       mod_utils,
       mod_admin_adminview
    ) {

// ============================================================================
// ROUTER
var AdminRouter = Backbone.Router.extend({

  // copied and pasted from libraries...
  initialize: function() {
    this.routesHit = 0;
    //keep count of number of routes handled by the application
    Backbone.history.on( 'route', function() { this.routesHit++; }, this );

},

routes: {
    "" : "admin_root",
},

// copied and pasted from libraries...
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

var GalaxyAdmin = Backbone.View.extend({

    initialize : function(){
        Galaxy.adminApp = this;

        this.adminRouter = new AdminRouter();

        this.adminRouter.on( 'route:admin_root', function() {
            console.log(mod_admin_adminview);
            var view = new mod_admin_adminview.AdminView();
            view.render();
        });

        Backbone.history.start({pushState: false});
    }
});

return {
    GalaxyApp: GalaxyAdmin
};

});
