define(["utils/utils","mvc/ui/ui-options"],function(b,a){var c=a.BaseIcons.extend({initialize:function(d){d.type=d.display||"checkbox";d.multiple=(d.display=="checkbox");a.BaseIcons.prototype.initialize.call(this,d);this.initial=true},value:function(d){var k=a.BaseIcons.prototype.value.call(this,d);if(this.initial&&k!==null&&this.header_index){this.initial=false;var e=k;if(!$.isArray(e)){e=[e]}for(var g in e){var h=this.header_index[e[g]];for(var f in h){this._setState(h[g],true)}}}return k},_setState:function(d,e){var f=this.$("#button-"+d);var g=this.$("#subgroup-"+d);f.data("is_expanded",e);if(e){g.fadeIn("fast");f.removeClass("toggle-expand");f.addClass("toggle")}else{g.hide();f.removeClass("toggle");f.addClass("toggle-expand")}},_templateOptions:function(g){var f=this;this.header_index={};this.header_list=[];function e(k,i){var l=k.find("#button-"+i);l.on("click",function(){f._setState(i,!l.data("is_expanded"))})}function d(r,t,o){o=o||[];for(h in t){var k=t[h];var l=k.options.length>0;var q=o.slice(0);var s=$("<div/>");if(l){var n=b.uuid();var i=$('<span id="button-'+n+'" class="ui-drilldown-button form-toggle icon-button toggle-expand"/>');var m=$('<div id="subgroup-'+n+'" style="display: none; margin-left: 25px;"/>');q.push(n);var p=$("<div/>");p.append(i);p.append(f._templateOption({label:k.name,value:k.value}));s.append(p);d(m,k.options,q);s.append(m);f.header_index[k.value]=q}else{s.append(f._templateOption({label:k.name,value:k.value}));f.header_index[k.value]=q}r.append(s)}}var j=$("<div/>");d(j,g);for(var h in this.header_index){this.header_list=_.uniq(this.header_list.concat(this.header_index[h]))}for(var h in this.header_list){e(j,this.header_list[h])}return j},_template:function(d){return'<div class="ui-options-list drilldown-container" id="'+d.id+'"/>'}});return{View:c}});