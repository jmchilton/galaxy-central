define(["utils/utils","mvc/ui/ui-table","mvc/ui/ui-misc","mvc/ui/ui-portlet","mvc/tools/tools-repeat","mvc/tools/tools-select-content","mvc/tools/tools-input"],function(e,b,h,d,c,a,f){var g=Backbone.View.extend({initialize:function(j,i){this.app=j;this.inputs=i.inputs;i.cls="ui-table-plain";i.cls_tr="section-row";this.table=new b.View(i);this.setElement(this.table.$el);this.render()},render:function(){this.table.delAll();for(var j in this.inputs){this.add(this.inputs[j])}},add:function(k){var j=this;var i=jQuery.extend(true,{},k);i.id=k.id=e.uuid();this.app.input_list[i.id]=i;var l=i.type;switch(l){case"conditional":this._addConditional(i);break;case"repeat":this._addRepeat(i);break;case"section":this._addSection(i);break;default:this._addRow(i)}},_addConditional:function(j){var k=this;j.test_param.id=j.id;var n=this._addRow(j.test_param);n.options.onchange=function(w){var v=k.app.tree.matchCase(j,w);for(var u in j.cases){var q=j.cases[u];var t=j.id+"-section-"+u;var p=k.table.get(t);var s=false;for(var r in q.inputs){if(!q.inputs[r].hidden){s=true;break}}if(u==v&&s){p.fadeIn("fast")}else{p.hide()}}k.app.trigger("refresh")};for(var m in j.cases){var l=j.id+"-section-"+m;var o=new g(this.app,{inputs:j.cases[m].inputs});o.$el.addClass("ui-table-form-section");this.table.add(o.$el);this.table.append(l)}n.trigger("change")},_addRepeat:function(p){var s=this;var q=0;function n(i,u){var t=p.id+"-section-"+(q++);var v=null;if(u){v=function(){l.del(t);l.retitle(p.title);s.app.trigger("refresh")}}var w=new g(s.app,{inputs:i});l.add({id:t,title:p.title,$el:w.$el,ondel:v});l.retitle(p.title)}var l=new c.View({title_new:p.title,max:p.max,onnew:function(){n(p.inputs,true);s.app.trigger("refresh")}});var j=p.min;var r=_.size(p.cache);for(var m=0;m<Math.max(r,j);m++){var o=null;if(m<r){o=p.cache[m]}else{o=p.inputs}n(o,m>=j)}var k=new f(this.app,{label:p.title,help:p.help,field:l});k.$el.addClass("ui-table-form-section");this.table.add(k.$el);this.table.append(p.id)},_addSection:function(i){var j=this;var n=new g(j.app,{inputs:i.inputs});var m=new h.ButtonIcon({icon:"fa-eye-slash",tooltip:"Show/hide section",cls:"ui-button-icon-plain"});var l=new d.View({title:i.label,cls:"ui-portlet-section",operations:{button_visible:m}});l.append(n.$el);l.append($("<div/>").addClass("ui-table-form-info").html(i.help));var k=false;l.$content.hide();l.$header.css("cursor","pointer");l.$header.on("click",function(){if(k){k=false;l.$content.hide();m.setIcon("fa-eye-slash")}else{k=true;l.$content.fadeIn("fast");m.setIcon("fa-eye")}});if(i.expand){l.$header.trigger("click")}this.table.add(l.$el);this.table.append(i.id)},_addRow:function(i){var l=i.id;var j=this._createField(i);this.app.field_list[l]=j;if(i.default_value===undefined){i.default_value=i.value}var k=new f(this.app,{label:i.label,default_value:i.default_value,optional:i.optional,help:i.help,field:j});this.app.element_list[l]=k;this.table.add(k.$el);this.table.append(l);if(i.hidden){this.table.get(l).hide()}return j},_createField:function(i){var j=null;switch(i.type){case"text":j=this._fieldText(i);break;case"select":j=this._fieldSelect(i);break;case"data":j=this._fieldData(i);break;case"data_collection":j=this._fieldData(i);break;case"data_column":i.error_text="Missing columns in referenced dataset.";j=this._fieldSelect(i);break;case"hidden":j=this._fieldHidden(i);break;case"hidden_data":j=this._fieldHidden(i);break;case"integer":j=this._fieldSlider(i);break;case"float":j=this._fieldSlider(i);break;case"boolean":j=this._fieldBoolean(i);break;case"genomebuild":i.searchable=true;j=this._fieldSelect(i);break;case"drill_down":j=this._fieldDrilldown(i);break;case"baseurl":j=this._fieldHidden(i);break;default:this.app.incompatible=true;if(i.options){j=this._fieldSelect(i)}else{j=this._fieldText(i)}console.debug("tools-form::_addRow() : Auto matched field type ("+i.type+").")}if(i.value!==undefined){j.value(i.value)}return j},_fieldData:function(i){if(!this.app.options.is_dynamic){i.info="Data input '"+i.name+"' ("+e.textify(i.extensions.toString())+")";i.value=null;return this._fieldHidden(i)}var j=this;return new a.View(this.app,{id:"field-"+i.id,extensions:i.extensions,optional:i.optional,multiple:i.multiple,type:i.type,data:i.options,onchange:function(){j.app.trigger("refresh")}})},_fieldSelect:function(j){if(!this.app.options.is_dynamic&&j.is_dynamic){return this._fieldText(j)}var l=[];for(var m in j.options){var n=j.options[m];l.push({label:n[0],value:n[1]})}var o=h.Select;switch(j.display){case"checkboxes":o=h.Checkbox;break;case"radio":o=h.Radio;break}var k=this;return new o.View({id:"field-"+j.id,data:l,error_text:j.error_text||"No options available",multiple:j.multiple,searchable:j.searchable,onchange:function(){k.app.trigger("refresh")}})},_fieldDrilldown:function(i){if(!this.app.options.is_dynamic&&i.is_dynamic){return this._fieldText(i)}var j=this;return new h.Drilldown.View({id:"field-"+i.id,data:i.options,display:i.display,onchange:function(){j.app.trigger("refresh")}})},_fieldText:function(i){if(i.options){i.area=i.multiple;if(!e.validate(i.value)){i.value=""}else{if(i.value instanceof Array){i.value=value.toString()}else{i.value=String(i.value).replace(/[\[\]'"\s]/g,"");if(i.multiple){i.value=i.value.replace(/,/g,"\n")}}}}var j=this;return new h.Input({id:"field-"+i.id,area:i.area,onchange:function(){j.app.trigger("refresh")}})},_fieldSlider:function(i){var j=this;return new h.Slider.View({id:"field-"+i.id,precise:i.type=="float",min:i.min,max:i.max,onchange:function(){j.app.trigger("refresh")}})},_fieldHidden:function(i){return new h.Hidden({id:"field-"+i.id,info:i.info})},_fieldBoolean:function(i){var j=this;return new h.RadioButton.View({id:"field-"+i.id,data:[{label:"Yes",value:"true"},{label:"No",value:"false"}],onchange:function(){j.app.trigger("refresh")}})}});return{View:g}});