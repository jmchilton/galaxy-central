define([],function(){return Backbone.View.extend({initialize:function(c,b){this.app=c;this.field=b.field;this.setElement(this._template(b));this.$field=this.$el.find(".ui-table-form-field");this.$title_optional=this.$el.find(".ui-table-form-title-optional");this.$error_text=this.$el.find(".ui-table-form-error-text");this.$error=this.$el.find(".ui-table-form-error");this.$field.prepend(this.field.$el);if(b.optional){this.field.skip=true}else{this.field.skip=false}this._refresh();var a=this;this.$title_optional.on("click",function(){a.field.skip=!a.field.skip;a._refresh()})},error:function(a){this.$error_text.html(a);this.$error.fadeIn();this.$el.addClass("ui-error")},reset:function(){this.$error.hide();this.$el.removeClass("ui-error")},_refresh:function(){if(!this.field.skip){this.$field.fadeIn("fast");this.$title_optional.html("Disable");this.app.refresh()}else{this.$field.hide();this.$title_optional.html("Enable")}},_template:function(a){var b='<div class="ui-table-form-element"><div class="ui-table-form-error ui-error"><span class="fa fa-arrow-down"/><span class="ui-table-form-error-text"/></div><div class="ui-table-form-title-strong">';if(a.optional){b+="Optional: "+a.label+'<span>&nbsp[<span class="ui-table-form-title-optional"/>]</span>'}else{b+=a.label}b+='</div><div class="ui-table-form-field">';if(a.help){b+='<div class="ui-table-form-info">'+a.help+"</div>"}b+="</div></div>";return b}})});