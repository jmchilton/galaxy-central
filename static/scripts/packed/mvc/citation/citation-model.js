define(["mvc/base-mvc","utils/localization"],function(a,e){var f=Backbone.Model.extend(a.LoggableMixin).extend({initialize:function(){var g=this.attributes.content;var i=new BibtexParser(g).entries[0];this.entry=i;this._fields={};var k=i.Fields;for(key in k){var j=k[key];var h=key.toLowerCase();this._fields[h]=j}},entryType:function(){return this.entry.EntryType},fields:function(){return this._fields}});var b=Backbone.Collection.extend(a.LoggableMixin).extend({urlRoot:galaxy_config.root+"api",partial:true,model:f,});var d=b.extend({url:function(){return this.urlRoot+"/histories/"+this.history_id+"/citations"}});var c=b.extend({url:function(){return this.urlRoot+"/tools/"+this.tool_id+"/citations"},partial:false,});return{Citation:f,HistoryCitationCollection:d,ToolCitationCollection:c}});