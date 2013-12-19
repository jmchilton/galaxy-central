jQuery.ajaxSettings.traditional=true;define(["mvc/ui"],function(){var a=Backbone.Model.extend({defaults:{url_base:"",async:false,async_ops:[],categorical_filters:[],filters:{},sort_key:null,show_item_checkboxes:false,advanced_search:false,cur_page:1,num_pages:1,operation:undefined,item_ids:undefined},can_async_op:function(c){return _.indexOf(this.attributes.async_ops,c)!==-1},add_filter:function(g,h,d){if(d){var e=this.attributes.filters[g],c;if(e===null||e===undefined){c=h}else{if(typeof(e)=="string"){if(e=="All"){c=h}else{var f=[];f[0]=e;f[1]=h;c=f}}else{c=e;c.push(h)}}this.attributes.filters[g]=c}else{this.attributes.filters[g]=h}},remove_filter:function(d,g){var c=this.attributes.filters[d];if(c===null||c===undefined){return false}var f=true;if(typeof(c)==="string"){if(c=="All"){f=false}else{delete this.attributes.filters[d]}}else{var e=_.indexOf(c,g);if(e!==-1){c.splice(e,1)}else{f=false}}return f},get_url_data:function(){var c={async:this.attributes.async,sort:this.attributes.sort_key,page:this.attributes.cur_page,show_item_checkboxes:this.attributes.show_item_checkboxes,advanced_search:this.attributes.advanced_search};if(this.attributes.operation){c.operation=this.attributes.operation}if(this.attributes.item_ids){c.id=this.attributes.item_ids}var d=this;_.each(_.pairs(d.attributes.filters),function(e){c["f-"+e[0]]=e[1]});return c},get_url:function(c){return this.get("url_base")+"?"+$.param(this.get_url_data())+"&"+$.param(c)}});var b=Backbone.View.extend({grid:null,initialize:function(c){this.init_grid(c);this.init_grid_controls();$("input[type=text]").each(function(){$(this).click(function(){$(this).select()}).keyup(function(){$(this).css("font-style","normal")})})},init_grid:function(e){this.grid=new a(e);var d=this.grid.attributes;var c=this.grid.get("url_base");c=c.replace(/^.*\/\/[^\/]+/,"");this.grid.set("url_base",c);$("#grid-table-body").html(this.template_body(d));$("#grid-table-footer").html(this.template_footer(d));if(d.message){$("#grid-message").html(this.template_message(d));setTimeout(function(){$("#grid-message").html("")},5000)}this.init_grid_elements()},init_grid_controls:function(){$(".submit-image").each(function(){$(this).mousedown(function(){$(this).addClass("gray-background")});$(this).mouseup(function(){$(this).removeClass("gray-background")})});var c=this;$(".sort-link").each(function(){$(this).click(function(){c.set_sort_condition($(this).attr("sort_key"));return false})});$(".categorical-filter > a").each(function(){$(this).click(function(){c.set_categorical_filter($(this).attr("filter_key"),$(this).attr("filter_val"));return false})});$(".text-filter-form").each(function(){$(this).submit(function(){var g=$(this).attr("column_key");var f=$("#input-"+g+"-filter");var h=f.val();f.val("");c.add_filter_condition(g,h);return false})});var d=$("#input-tags-filter");if(d.length){d.autocomplete(this.grid.history_tag_autocomplete_url,{selectFirst:false,autoFill:false,highlight:false,mustMatch:false})}var e=$("#input-name-filter");if(e.length){e.autocomplete(this.grid.history_name_autocomplete_url,{selectFirst:false,autoFill:false,highlight:false,mustMatch:false})}$(".advanced-search-toggle").each(function(){$(this).click(function(){$("#standard-search").slideToggle("fast");$("#advanced-search").slideToggle("fast");return false})})},init_grid_elements:function(){$(".grid").each(function(){var r=$(this).find("input.grid-row-select-checkbox");var q=$(this).find("span.grid-selected-count");var s=function(){q.text($(r).filter(":checked").length)};$(r).each(function(){$(this).change(s)});s()});if($(".community_rating_star").length!==0){$(".community_rating_star").rating({})}var p=this.grid.attributes;var o=this;$(".page-link > a").each(function(){$(this).click(function(){o.set_page($(this).attr("page_num"));return false})});$(".use-inbound").each(function(){$(this).click(function(q){o.execute({href:$(this).attr("href"),inbound:true});return false})});$(".use-outbound").each(function(){$(this).click(function(q){o.execute({href:$(this).attr("href")});return false})});for(var h in p.items){var k=$("#grid-"+h+"-popup");k.off();var d=new PopupMenu(k);var n=p.items[h];for(var g in p.operations){var e=p.operations[g];var l=e.label;var c=n.operation_config[l];var f=n.encode_id;if(c.allowed&&e.allow_popup){var m={html:e.label,href:c.url_args,target:c.target,confirmation_text:e.confirm,inbound:e.inbound};m.func=function(s){s.preventDefault();var r=$(s.target).html();var q=this.findItemByHtml(r);o.execute(q)};d.addItem(m)}}}},add_filter_condition:function(e,g){if(g===""){return false}this.grid.add_filter(e,g,true);var f=$("<span>"+g+"<a href='javascript:void(0);'><span class='delete-search-icon' /></span></a>");f.addClass("text-filter-val");var d=this;f.click(function(){d.grid.remove_filter(e,g);$(this).remove();d.go_page_one();d.execute()});var c=$("#"+e+"-filtering-criteria");c.append(f);this.go_page_one();this.execute()},set_sort_condition:function(h){var g=this.grid.get("sort_key");var f=h;if(g.indexOf(h)!==-1){if(g.substring(0,1)!=="-"){f="-"+h}else{}}$(".sort-arrow").remove();var e=(f.substring(0,1)=="-")?"&uarr;":"&darr;";var c=$("<span>"+e+"</span>").addClass("sort-arrow");var d=$("#"+h+"-header");d.append(c);this.grid.set("sort_key",f);this.go_page_one();this.execute()},set_categorical_filter:function(e,g){var d=this.grid.get("categorical_filters")[e],f=this.grid.get("filters")[e];var c=this;$("."+e+"-filter").each(function(){var m=$.trim($(this).text());var k=d[m];var l=k[e];if(l==g){$(this).empty();$(this).addClass("current-filter");$(this).append(m)}else{if(l==f){$(this).empty();var h=$("<a href='#'>"+m+"</a>");h.click(function(){c.set_categorical_filter(e,l)});$(this).removeClass("current-filter");$(this).append(h)}}});this.grid.add_filter(e,g);this.go_page_one();this.execute()},set_page:function(c){var d=this;$(".page-link").each(function(){var k=$(this).attr("id"),g=parseInt(k.split("-")[2],10),e=d.grid.get("cur_page"),h;if(g===c){h=$(this).children().text();$(this).empty();$(this).addClass("inactive-link");$(this).text(h)}else{if(g===e){h=$(this).text();$(this).empty();$(this).removeClass("inactive-link");var f=$("<a href='#'>"+h+"</a>");f.click(function(){d.set_page(g)});$(this).append(f)}}});if(c==="all"){this.grid.set("cur_page",c)}else{this.grid.set("cur_page",parseInt(c,10))}this.execute()},submit_operation:function(f,g){var e=$('input[name="id"]:checked').length;if(!e>0){return false}var d=$(f).val();var c=[];$("input[name=id]:checked").each(function(){c.push($(this).val())});this.execute({operation:d,id:c,confirmation_text:g});return true},execute:function(n){var f=null;var e=null;var g=null;var c=null;var m=null;if(n){e=n.href;g=n.operation;f=n.id;c=n.confirmation_text;m=n.inbound;if(e!==undefined&&e.indexOf("operation=")!=-1){var l=e.split("?");if(l.length>1){var k=l[1];var d=k.split("&");for(var h=0;h<d.length;h++){if(d[h].indexOf("operation")!=-1){g=d[h].split("=")[1];g=g.replace(/\+/g," ")}else{if(d[h].indexOf("id")!=-1){f=d[h].split("=")[1]}}}}}}if(g&&f){if(c&&c!=""&&c!="None"&&c!="null"){if(!confirm(c)){return false}}g=g.toLowerCase();this.grid.set({operation:g,item_ids:f});if(this.grid.can_async_op(g)){this.update_grid()}else{this.go_to(m,"")}return false}if(e){this.go_to(m,e);return false}if(this.grid.get("async")){this.update_grid()}else{this.go_to(m,"")}return false},go_to:function(f,d){var e=this.grid.get("async");this.grid.set("async",false);advanced_search=$("#advanced-search").is(":visible");this.grid.set("advanced_search",advanced_search);if(!d){d=this.grid.get("url_base")+"?"+$.param(this.grid.get_url_data())}this.grid.set({operation:undefined,item_ids:undefined,async:e});if(f){var c=$(".grid-header").closest(".inbound");if(c.length!==0){c.load(d);return}}window.location=d},update_grid:function(){var d=(this.grid.get("operation")?"POST":"GET");$(".loading-elt-overlay").show();var c=this;$.ajax({type:d,url:c.grid.get("url_base"),data:c.grid.get_url_data(),error:function(e){alert("Grid refresh failed")},success:function(e){c.init_grid($.parseJSON(e));$("#grid-table-body").trigger("update");$(".loading-elt-overlay").hide()},complete:function(){c.grid.set({operation:undefined,item_ids:undefined})}})},check_all_items:function(){var c=document.getElementById("check_all"),d=document.getElementsByTagName("input"),f=0,e;if(c.checked===true){for(e=0;e<d.length;e++){if(d[e].name.indexOf("id")!==-1){d[e].checked=true;f++}}}else{for(e=0;e<d.length;e++){if(d[e].name.indexOf("id")!==-1){d[e].checked=false}}}this.init_grid_elements()},go_page_one:function(){var c=this.grid.get("cur_page");if(c!==null&&c!==undefined&&c!=="all"){this.grid.set("cur_page",1)}},template_body:function(s){var l="";var t=0;var g=s.items.length;if(g==0){l+='<tr><td colspan="100"><em>No Items</em></td></tr>';t=1}for(i in s.items){var q=s.items[i];var c=q.encode_id;var h="grid-"+i+"-popup";l+="<tr ";if(s.current_item_id==q.id){l+='class="current"'}l+=">";if(s.show_item_checkboxes){l+='<td style="width: 1.5em;"><input type="checkbox" name="id" value="'+c+'" id="'+c+'" class="grid-row-select-checkbox" /></td>'}for(j in s.columns){var f=s.columns[j];if(f.visible){var e="";if(f.nowrap){e='style="white-space:nowrap;"'}var r=q.column_config[f.label];var k=r.link;var m=r.value;var p=r.inbound;if(jQuery.type(m)==="string"){m=m.replace(/\/\//g,"/")}var d="";var o="";if(f.attach_popup){d="grid-"+i+"-popup";o="menubutton";if(k!=""){o+=" split"}o+=" popup"}l+="<td "+e+">";if(k){if(s.operations.length!=0){l+='<div id="'+d+'" class="'+o+'" style="float: left;">'}var n="";if(p){n="use-inbound"}else{n="use-outbound"}l+='<a class="label '+n+'" href="'+k+'" onclick="return false;">'+m+"</a>";if(s.operations.length!=0){l+="</div>"}}else{l+='<div id="'+d+'" class="'+o+'"><label id="'+f.label_id_prefix+c+'" for="'+c+'">'+m+"</label></div>"}l+="</td>"}}l+="</tr>";t++}return l},template_footer:function(q){var m="";if(q.use_paging&&q.num_pages>1){var o=q.num_page_links;var c=q.cur_page_num;var p=q.num_pages;var l=o/2;var k=c-l;var g=0;if(k==0){k=1;g=l-(c-k)}var f=l+g;var e=c+f;if(e<=p){max_offset=0}else{e=p;max_offset=f-(e+1-c)}if(max_offset!=0){k-=max_offset;if(k<1){k=1}}m+='<tr id="page-links-row">';if(q.show_item_checkboxes){m+="<td></td>"}m+='<td colspan="100"><span id="page-link-container">Page:';if(k>1){m+='<span class="page-link" id="page-link-1"><a href="'+this.grid.get_url({page:n})+'" page_num="1" onclick="return false;">1</a></span> ...'}for(var n=k;n<e+1;n++){if(n==q.cur_page_num){m+='<span class="page-link inactive-link" id="page-link-'+n+'">'+n+"</span>"}else{m+='<span class="page-link" id="page-link-'+n+'"><a href="'+this.grid.get_url({page:n})+'" onclick="return false;" page_num="'+n+'">'+n+"</a></span>"}}if(e<p){m+='...<span class="page-link" id="page-link-'+p+'"><a href="'+this.grid.get_url({page:p})+'" onclick="return false;" page_num="'+p+'">'+p+"</a></span>"}m+="</span>";m+='<span class="page-link" id="show-all-link-span"> | <a href="'+this.grid.get_url({page:"all"})+'" onclick="return false;" page_num="all">Show All</a></span></td></tr>'}if(q.show_item_checkboxes){m+='<tr><input type="hidden" id="operation" name="operation" value=""><td></td><td colspan="100">For <span class="grid-selected-count"></span> selected '+q.get_class_plural+": ";for(i in q.operations){var d=q.operations[i];if(d.allow_multiple){m+='<input type="button" value="'+d.label+'" class="action-button" onclick="gridView.submit_operation(this, \''+d.confirm+"')\"> "}}m+="</td></tr>"}var h=false;for(i in q.operations){if(q.operations[i].global_operation){h=true;break}}if(h){m+='<tr><td colspan="100">';for(i in q.operations){var d=q.operations[i];if(d.global_operation){m+='<a class="action-button" href="'+d.global_operation+'">'+d.label+"</a>"}}m+="</td></tr>"}if(q.legend){m+='<tr><td colspan="100">'+q.legend+"</td></tr>"}return m},template_message:function(c){return'<p><div class="'+c.status+'message transient-message">'+c.message+'</div><div style="clear: both"></div></p>'}});return{Grid:a,GridView:b}});