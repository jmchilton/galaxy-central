define(["utils/utils"],function(a){var b=Backbone.View.extend({optionsDefault:{id:"",cls:"",error_text:"No data available",empty_text:"No selection",visible:true,wait:false,multiple:false,searchable:false,optional:false},initialize:function(d){this.options=a.merge(d,this.optionsDefault);this.setElement(this._template(this.options));this.$select=this.$el.find(".select");this.$icon=this.$el.find(".icon");this.$button=this.$el.find(".button");if(this.options.multiple){this.$select.prop("multiple",true);this.$select.addClass("ui-select-multiple");this.$icon.remove()}else{this.$el.addClass("ui-select")}this.update(this.options.data);if(this.options.value!==undefined){this.value(this.options.value)}if(!this.options.visible){this.hide()}if(this.options.wait){this.wait()}else{this.show()}var c=this;this.$select.on("change",function(){c._change()});this.on("change",function(){c._change()})},value:function(c){if(c!==undefined){this.$select.val(c);if(this.$select.select2){this.$select.select2("val",c)}}return this.$select.val()},first:function(){var c=this.$select.find("option");if(c.length>0){return c.val()}else{return undefined}},validate:function(){return a.validate(this.value())},text:function(){return this.$select.find("option:selected").text()},show:function(){this.unwait();this.$select.show();this.$el.show()},hide:function(){this.$el.hide()},wait:function(){this.$icon.removeClass();this.$icon.addClass("fa fa-spinner fa-spin")},unwait:function(){this.$icon.removeClass();this.$icon.addClass("fa fa-caret-down")},disabled:function(){return this.$select.is(":disabled")},enable:function(){this.$select.prop("disabled",false)},disable:function(){this.$select.prop("disabled",true)},add:function(c){this.$select.append(this._templateOption(c));this._refresh()},del:function(c){this.$select.find("option[value="+c+"]").remove();this.$select.trigger("change");this._refresh()},update:function(c){var e=this.$select.val();this.$select.find("option").remove();if(this.options.optional&&!this.options.multiple){this.$select.append(this._templateOption({value:"__null__",label:this.options.empty_text}))}for(var d in c){this.$select.append(this._templateOption(c[d]))}this._refresh();this.$select.val(e);if(!this.$select.val()){this.$select.val(this.first())}if(this.options.searchable){this.$button.hide();this.$select.select2("destroy");this.$select.select2()}},setOnChange:function(c){this.options.onchange=c},exists:function(c){return this.$select.find('option[value="'+c+'"]').length>0},_change:function(){if(this.options.onchange){this.options.onchange(this.$select.val())}},_refresh:function(){this.$select.find('option[value="__undefined__"]').remove();var c=this.$select.find("option").length;if(c==0){this.disable();this.$select.append(this._templateOption({value:"__undefined__",label:this.options.error_text}))}else{this.enable()}},_templateOption:function(c){return'<option value="'+c.value+'">'+c.label+"</option>"},_template:function(c){return'<div id="'+c.id+'"><select id="select" class="select '+c.cls+" "+c.id+'"></select><div class="button"><i class="icon"/></div></div>'}});return{View:b}});