define([
],
function() {

var AdminView = Backbone.View.extend({
  el: '#center',

  render: function() {
  	this.$el.html(this.template({}));
  },

  template: function() {
  	return _.template([
    	"<p>This is the admin application.</p>",
    ].join(''));
  },

});

return {
    AdminView: AdminView
};

});