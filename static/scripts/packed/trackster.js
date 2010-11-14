var DENSITY=200,FEATURE_LEVELS=10,MAX_FEATURE_DEPTH=50,CONNECTOR_COLOR="#ccc",DATA_ERROR="There was an error in indexing this dataset.",DATA_NOCONVERTER="A converter for this dataset is not installed. Please check your datatypes_conf.xml file.",DATA_NONE="No data for this chrom/contig.",DATA_PENDING="Currently indexing... please wait",DATA_LOADING="Loading data...",FILTERABLE_CLASS="filterable",CACHED_TILES_FEATURE=10,CACHED_TILES_LINE=5,CACHED_DATA=5,DUMMY_CANVAS=document.createElement("canvas"),RIGHT_STRAND,LEFT_STRAND;if(window.G_vmlCanvasManager){G_vmlCanvasManager.initElement(DUMMY_CANVAS)}CONTEXT=DUMMY_CANVAS.getContext("2d");PX_PER_CHAR=CONTEXT.measureText("A").width;var right_img=new Image();right_img.src=image_path+"/visualization/strand_right.png";right_img.onload=function(){RIGHT_STRAND=CONTEXT.createPattern(right_img,"repeat")};var left_img=new Image();left_img.src=image_path+"/visualization/strand_left.png";left_img.onload=function(){LEFT_STRAND=CONTEXT.createPattern(left_img,"repeat")};var right_img_inv=new Image();right_img_inv.src=image_path+"/visualization/strand_right_inv.png";right_img_inv.onload=function(){RIGHT_STRAND_INV=CONTEXT.createPattern(right_img_inv,"repeat")};var left_img_inv=new Image();left_img_inv.src=image_path+"/visualization/strand_left_inv.png";left_img_inv.onload=function(){LEFT_STRAND_INV=CONTEXT.createPattern(left_img_inv,"repeat")};function round_1000(a){return Math.round(a*1000)/1000}var Cache=function(a){this.num_elements=a;this.clear()};$.extend(Cache.prototype,{get:function(b){var a=this.key_ary.indexOf(b);if(a!=-1){this.key_ary.splice(a,1);this.key_ary.push(b)}return this.obj_cache[b]},set:function(b,c){if(!this.obj_cache[b]){if(this.key_ary.length>=this.num_elements){var a=this.key_ary.shift();delete this.obj_cache[a]}this.key_ary.push(b)}this.obj_cache[b]=c;return c},clear:function(){this.obj_cache={};this.key_ary=[]}});var View=function(a,d,c,b,e){this.container=a;this.vis_id=c;this.dbkey=b;this.title=d;this.tracks=[];this.label_tracks=[];this.max_low=0;this.max_high=0;this.num_tracks=0;this.track_id_counter=0;this.zoom_factor=3;this.min_separation=30;this.has_changes=false;this.init(e);this.reset()};$.extend(View.prototype,{init:function(d){var c=this.container,a=this;this.top_container=$("<div/>").addClass("top-container").appendTo(c);this.content_div=$("<div/>").addClass("content").css("position","relative").appendTo(c);this.bottom_container=$("<div/>").addClass("bottom-container").appendTo(c);this.top_labeltrack=$("<div/>").addClass("top-labeltrack").appendTo(this.top_container);this.viewport_container=$("<div/>").addClass("viewport-container").addClass("viewport-container").appendTo(this.content_div);this.intro_div=$("<div/>").addClass("intro").text("Select a chrom from the dropdown below").hide();this.nav_labeltrack=$("<div/>").addClass("nav-labeltrack").appendTo(this.bottom_container);this.nav_container=$("<div/>").addClass("nav-container").prependTo(this.top_container);this.nav=$("<div/>").addClass("nav").appendTo(this.nav_container);this.overview=$("<div/>").addClass("overview").appendTo(this.bottom_container);this.overview_viewport=$("<div/>").addClass("overview-viewport").appendTo(this.overview);this.overview_close=$("<a href='javascript:void(0);'>Close Overview</a>").addClass("overview-close").hide().appendTo(this.overview_viewport);this.overview_highlight=$("<div />").addClass("overview-highlight").hide().appendTo(this.overview_viewport);this.overview_box_background=$("<div/>").addClass("overview-boxback").appendTo(this.overview_viewport);this.overview_box=$("<div/>").addClass("overview-box").appendTo(this.overview_viewport);this.default_overview_height=this.overview_box.height();this.nav_controls=$("<div/>").addClass("nav-controls").appendTo(this.nav);this.chrom_form=$("<form/>").attr("action",function(){}).appendTo(this.nav_controls);this.chrom_select=$("<select/>").attr({name:"chrom"}).css("width","15em").addClass("no-autocomplete").append("<option value=''>Loading</option>").appendTo(this.chrom_form);var b=function(f){if(f.type==="focusout"||(f.keyCode||f.which)===13||(f.keyCode||f.which)===27){if((f.keyCode||f.which)!==27){a.go_to($(this).val())}$(this).hide();a.location_span.show();a.chrom_select.show();return false}};this.nav_input=$("<input/>").addClass("nav-input").hide().bind("keypress focusout",b).appendTo(this.chrom_form);this.location_span=$("<span/>").addClass("location").appendTo(this.chrom_form);this.location_span.bind("click",function(){a.location_span.hide();a.chrom_select.hide();a.nav_input.css("display","inline-block");a.nav_input.select();a.nav_input.focus()});if(this.vis_id!==undefined){this.hidden_input=$("<input/>").attr("type","hidden").val(this.vis_id).appendTo(this.chrom_form)}this.zo_link=$("<a id='zoom-out' />").click(function(){a.zoom_out();a.redraw()}).appendTo(this.chrom_form);this.zi_link=$("<a id='zoom-in' />").click(function(){a.zoom_in();a.redraw()}).appendTo(this.chrom_form);$.ajax({url:chrom_url,data:(this.vis_id!==undefined?{vis_id:this.vis_id}:{dbkey:this.dbkey}),dataType:"json",success:function(f){if(f.reference){a.add_label_track(new ReferenceTrack(a))}a.chrom_data=f.chrom_info;var j='<option value="">Select Chrom/Contig</option>';for(var h=0,e=a.chrom_data.length;h<e;h++){var g=a.chrom_data[h].chrom;j+='<option value="'+g+'">'+g+"</option>"}a.chrom_select.html(j);a.intro_div.show();a.chrom_select.bind("change",function(){a.change_chrom(a.chrom_select.val())});if(d){d()}},error:function(){alert("Could not load chroms for this dbkey:",a.dbkey)}});this.content_div.bind("dblclick",function(f){a.zoom_in(f.pageX,this.viewport_container)});this.overview_box.bind("dragstart",function(f){this.current_x=f.offsetX}).bind("drag",function(f){var h=f.offsetX-this.current_x;this.current_x=f.offsetX;var g=Math.round(h/a.viewport_container.width()*(a.max_high-a.max_low));a.move_delta(-g)});this.overview_close.bind("click",function(){for(var f=0,e=a.tracks.length;f<e;f++){a.tracks[f].is_overview=false}$(this).siblings().filter("canvas").remove();$(this).parent().css("height",a.overview_box.height());a.overview_highlight.hide();$(this).hide()});this.viewport_container.bind("dragstart",function(f){this.original_low=a.low;this.current_height=f.clientY;this.current_x=f.offsetX;this.enable_pan=(f.clientX<a.viewport_container.width()-16)?true:false}).bind("drag",function(h){if(!this.enable_pan||this.in_reordering){return}var f=$(this);var j=h.offsetX-this.current_x;var g=f.scrollTop()-(h.clientY-this.current_height);f.scrollTop(g);this.current_height=h.clientY;this.current_x=h.offsetX;var i=Math.round(j/a.viewport_container.width()*(a.high-a.low));a.move_delta(i)});this.top_labeltrack.bind("dragstart",function(f){this.drag_origin_x=f.clientX;this.drag_origin_pos=f.clientX/a.viewport_container.width()*(a.high-a.low)+a.low;this.drag_div=$("<div />").css({height:a.content_div.height()+a.top_labeltrack.height()+a.nav_labeltrack.height(),top:"0px",position:"absolute","background-color":"#ccf",opacity:0.5,"z-index":1000}).appendTo($(this))}).bind("drag",function(j){var g=Math.min(j.clientX,this.drag_origin_x)-a.container.offset().left,f=Math.max(j.clientX,this.drag_origin_x)-a.container.offset().left,i=(a.high-a.low),h=a.viewport_container.width();a.update_location(Math.round(g/h*i)+a.low,Math.round(f/h*i)+a.low);this.drag_div.css({left:g+"px",width:(f-g)+"px"})}).bind("dragend",function(k){var g=Math.min(k.clientX,this.drag_origin_x),f=Math.max(k.clientX,this.drag_origin_x),i=(a.high-a.low),h=a.viewport_container.width(),j=a.low;a.low=Math.round(g/h*i)+j;a.high=Math.round(f/h*i)+j;this.drag_div.remove();a.redraw()});this.add_label_track(new LabelTrack(this,this.top_labeltrack));this.add_label_track(new LabelTrack(this,this.nav_labeltrack));$(window).bind("resize",function(){a.resize_window()});$(document).bind("redraw",function(){a.redraw()});this.reset();$(window).trigger("resize")},update_location:function(a,b){this.location_span.text(commatize(a)+" - "+commatize(b));this.nav_input.val(this.chrom+":"+commatize(a)+"-"+commatize(b))},change_chrom:function(e,b,g){var d=this;var f=$.grep(d.chrom_data,function(j,k){return j.chrom===e})[0];if(f===undefined){return}if(e!==d.chrom){d.chrom=e;if(!d.chrom){d.intro_div.show()}else{d.intro_div.hide()}d.chrom_select.val(d.chrom);d.max_high=f.len;d.reset();d.redraw(true);for(var h=0,a=d.tracks.length;h<a;h++){var c=d.tracks[h];if(c.init){c.init()}}}if(b!==undefined&&g!==undefined){d.low=Math.max(b,0);d.high=Math.min(g,d.max_high)}d.reset_overview();d.redraw()},go_to:function(f){var j=this,a,d,b=f.split(":"),h=b[0],i=b[1];if(i!==undefined){try{var g=i.split("-");a=parseInt(g[0].replace(/,/g,""),10);d=parseInt(g[1].replace(/,/g,""),10)}catch(c){return false}}j.change_chrom(h,a,d)},move_fraction:function(c){var a=this;var b=a.high-a.low;this.move_delta(c*b)},move_delta:function(c){var a=this;var b=a.high-a.low;if(a.low-c<a.max_low){a.low=a.max_low;a.high=a.max_low+b}else{if(a.high-c>a.max_high){a.high=a.max_high;a.low=a.max_high-b}else{a.high-=c;a.low-=c}}a.redraw()},add_track:function(a){a.view=this;a.track_id=this.track_id_counter;this.tracks.push(a);if(a.init){a.init()}a.container_div.attr("id","track_"+a.track_id);this.track_id_counter+=1;this.num_tracks+=1},add_label_track:function(a){a.view=this;this.label_tracks.push(a)},remove_track:function(a){this.has_changes=true;a.container_div.fadeOut("slow",function(){$(this).remove()});delete this.tracks[this.tracks.indexOf(a)];this.num_tracks-=1},reset:function(){this.low=this.max_low;this.high=this.max_high;this.viewport_container.find(".yaxislabel").remove()},redraw:function(h){var g=this.high-this.low,f=this.low,b=this.high;if(f<this.max_low){f=this.max_low}if(b>this.max_high){b=this.max_high}if(this.high!==0&&g<this.min_separation){b=f+this.min_separation}this.low=Math.floor(f);this.high=Math.ceil(b);this.resolution=Math.pow(10,Math.ceil(Math.log((this.high-this.low)/200)/Math.LN10));this.zoom_res=Math.pow(FEATURE_LEVELS,Math.max(0,Math.ceil(Math.log(this.resolution,FEATURE_LEVELS)/Math.log(FEATURE_LEVELS))));var a=(this.low/(this.max_high-this.max_low)*this.overview_viewport.width())||0;var e=((this.high-this.low)/(this.max_high-this.max_low)*this.overview_viewport.width())||0;var j=13;this.overview_box.css({left:a,width:Math.max(j,e)}).show();if(e<j){this.overview_box.css("left",a-(j-e)/2)}if(this.overview_highlight){this.overview_highlight.css({left:a,width:e})}this.update_location(this.low,this.high);if(!h){for(var c=0,d=this.tracks.length;c<d;c++){if(this.tracks[c]&&this.tracks[c].enabled){this.tracks[c].draw()}}for(c=0,d=this.label_tracks.length;c<d;c++){this.label_tracks[c].draw()}}},zoom_in:function(b,c){if(this.max_high===0||this.high-this.low<this.min_separation){return}var d=this.high-this.low,e=d/2+this.low,a=(d/this.zoom_factor)/2;if(b){e=b/this.viewport_container.width()*(this.high-this.low)+this.low}this.low=Math.round(e-a);this.high=Math.round(e+a);this.redraw()},zoom_out:function(){if(this.max_high===0){return}var b=this.high-this.low,c=b/2+this.low,a=(b*this.zoom_factor)/2;this.low=Math.round(c-a);this.high=Math.round(c+a);this.redraw()},resize_window:function(){this.viewport_container.height(this.container.height()-this.top_container.height()-this.bottom_container.height());this.nav_container.width(this.container.width());this.redraw()},reset_overview:function(){this.overview_viewport.find("canvas").remove();this.overview_viewport.height(this.default_overview_height);this.overview_box.height(this.default_overview_height);this.overview_close.hide();this.overview_highlight.hide()}});var Filter=function(b,a,c){this.name=b;this.index=a;this.value=c};var NumberFilter=function(b,a){this.name=b;this.index=a;this.low=-Number.MAX_VALUE;this.high=Number.MAX_VALUE;this.slider_min=Number.MAX_VALUE;this.slider_max=-Number.MAX_VALUE;this.slider=null;this.slider_label=null};$.extend(NumberFilter.prototype,{applies_to:function(a){if(a.length>this.index){return true}return false},keep:function(a){if(!this.applies_to(a)){return true}return(a[this.index]>=this.low&&a[this.index]<=this.high)},update_attrs:function(b){var a=false;if(!this.applies_to(b)){return a}if(b[this.index]<this.slider_min){this.slider_min=b[this.index];a=true}if(b[this.index]>this.slider_max){this.slider_max=b[this.index];a=false}return a},update_ui_elt:function(){var b=this.slider.slider("option","min"),a=this.slider.slider("option","max");if(this.slider_min<b||this.slider_max>a){this.slider.slider("option","min",this.slider_min);this.slider.slider("option","max",this.slider_max);this.slider.slider("option","values",[this.slider_min,this.slider_max])}}});var get_filters=function(a){var g=[];for(var d=0;d<a.length;d++){var f=a[d];var c=f.name,e=f.type,b=f.index;if(e=="int"||e=="float"){g[d]=new NumberFilter(c,b)}else{g[d]=new Filter(c,b,e)}}return g};var Track=function(b,a,d,c){this.name=b;this.view=a;this.parent_element=d;this.filters=(c!==undefined?get_filters(c):[]);this.init_global()};$.extend(Track.prototype,{init_global:function(){this.container_div=$("<div />").addClass("track").css("position","relative");if(!this.hidden){this.header_div=$("<div class='track-header' />").appendTo(this.container_div);if(this.view.editor){this.drag_div=$("<div class='draghandle' />").appendTo(this.header_div)}this.name_div=$("<div class='menubutton popup' />").appendTo(this.header_div);this.name_div.text(this.name);this.name_div.attr("id",this.name.replace(/\s+/g,"-").replace(/[^a-zA-Z0-9\-]/g,"").toLowerCase())}this.filtering_div=$("<div class='track-filters'>").appendTo(this.container_div);this.filtering_div.hide();this.filtering_div.bind("drag",function(i){i.stopPropagation()});var b=$("<table class='filters'>").appendTo(this.filtering_div);var c=this;for(var e=0;e<this.filters.length;e++){var a=this.filters[e];var f=$("<tr>").appendTo(b);var g=$("<th class='filter-info'>").appendTo(f);var j=$("<span class='name'>").appendTo(g);j.text(a.name+"  ");var d=$("<span class='values'>").appendTo(g);var h=$("<td>").appendTo(f);a.control_element=$("<div id='"+a.name+"-filter-control' style='width: 200px; position: relative'>").appendTo(h);a.control_element.slider({range:true,min:Number.MAX_VALUE,max:-Number.MIN_VALUE,values:[0,0],slide:function(k,l){var i=l.values;d.text("["+i[0]+"-"+i[1]+"]");a.low=i[0];a.high=i[1];c.draw(true)},change:function(i,k){a.control_element.slider("option","slide").call(a.control_element,i,k)}});a.slider=a.control_element;a.slider_label=d}this.content_div=$("<div class='track-content'>").appendTo(this.container_div);this.parent_element.append(this.container_div)},init_each:function(c,b){var a=this;a.enabled=false;a.data_queue={};a.tile_cache.clear();a.data_cache.clear();a.initial_canvas=undefined;a.content_div.css("height","auto");if(!a.content_div.text()){a.content_div.text(DATA_LOADING)}a.container_div.removeClass("nodata error pending");if(a.view.chrom){$.getJSON(data_url,c,function(d){if(!d||d==="error"||d.kind==="error"){a.container_div.addClass("error");a.content_div.text(DATA_ERROR);if(d.message){var f=a.view.tracks.indexOf(a);var e=$("<a href='javascript:void(0);'></a>").attr("id",f+"_error");e.text("Click to view error");$("#"+f+"_error").live("click",function(){show_modal("Trackster Error","<pre>"+d.message+"</pre>",{Close:hide_modal})});a.content_div.append(e)}}else{if(d==="no converter"){a.container_div.addClass("error");a.content_div.text(DATA_NOCONVERTER)}else{if(d.data!==undefined&&(d.data===null||d.data.length===0)){a.container_div.addClass("nodata");a.content_div.text(DATA_NONE)}else{if(d==="pending"){a.container_div.addClass("pending");a.content_div.text(DATA_PENDING);setTimeout(function(){a.init()},5000)}else{a.content_div.text("");a.content_div.css("height",a.height_px+"px");a.enabled=true;b(d);a.draw()}}}}})}else{a.container_div.addClass("nodata");a.content_div.text(DATA_NONE)}}});var TiledTrack=function(){var b=this,j=b.view;if(b.hidden){return}if(b.display_modes!==undefined){if(b.mode_div===undefined){b.mode_div=$("<div class='right-float menubutton popup' />").appendTo(b.header_div);var e=b.display_modes[0];b.mode=e;b.mode_div.text(e);var c=function(i){b.mode_div.text(i);b.mode=i;b.tile_cache.clear();b.draw()};var a={};for(var f=0,h=b.display_modes.length;f<h;f++){var g=b.display_modes[f];a[g]=function(i){return function(){c(i)}}(g)}make_popupmenu(b.mode_div,a)}else{b.mode_div.hide()}}var d={};d["Set as overview"]=function(){j.overview_viewport.find("canvas").remove();b.is_overview=true;b.set_overview();for(var i in j.tracks){if(j.tracks[i]!==b){j.tracks[i].is_overview=false}}};d["Edit configuration"]=function(){var l=function(){hide_modal();$(window).unbind("keypress.check_enter_esc")},i=function(){b.update_options(b.track_id);hide_modal();$(window).unbind("keypress.check_enter_esc")},k=function(m){if((m.keyCode||m.which)===27){l()}else{if((m.keyCode||m.which)===13){i()}}};$(window).bind("keypress.check_enter_esc",k);show_modal("Configure Track",b.gen_options(b.track_id),{Cancel:l,OK:i})};if(b.filters.length>0){d["Show filters"]=function(){var i;if(!b.filtering_div.is(":visible")){i="Hide filters";b.filters_visible=true}else{i="Show filters";b.filters_visible=false}$("#"+b.name_div.attr("id")+"-menu").find("li").eq(2).text(i);b.filtering_div.toggle()}}d.Remove=function(){j.remove_track(b);if(j.num_tracks===0){$("#no-tracks").show()}};b.popup_menu=make_popupmenu(b.name_div,d);show_hide_popupmenu_options(b.popup_menu,"(Show|Hide) filters",false)};$.extend(TiledTrack.prototype,Track.prototype,{draw:function(a){var k=this.view.low,g=this.view.high,h=g-k,f=this.view.resolution;var n=$("<div style='position: relative;'></div>"),o=this.content_div.width()/h;this.content_div.append(n);this.max_height=0;var b=Math.floor(k/f/DENSITY);var j={};while((b*DENSITY*f)<g){var l=this.content_div.width()+"_"+o+"_"+b;var e=this.tile_cache.get(l);if(!a&&e){var i=b*DENSITY*f;var d=(i-k)*o;if(this.left_offset){d-=this.left_offset}e.css({left:d});this.show_tile(e,n)}else{this.delayed_draw(this,l,k,g,b,f,n,o,j)}b+=1}var c=this;var m=setInterval(function(){if(obj_length(j)===0){if(c.content_div.children().length>1){c.content_div.children(":first").remove()}for(var p=0;p<c.filters.length;p++){c.filters[p].update_ui_elt()}clearInterval(m)}},50)},delayed_draw:function(c,h,g,e,b,d,i,j,f){var a=setTimeout(function(){if(g<=c.view.high&&e>=c.view.low){var k=c.draw_tile(d,b,i,j);if(k){if(!c.initial_canvas&&!window.G_vmlCanvasManager){c.initial_canvas=$(k).clone();var n=k.get(0).getContext("2d");var l=c.initial_canvas.get(0).getContext("2d");var m=n.getImageData(0,0,n.canvas.width,n.canvas.height);l.putImageData(m,0,0);c.set_overview()}c.tile_cache.set(h,k);c.show_tile(k,i)}}delete f[a]},50);f[a]=true},show_tile:function(a,c){var b=this;c.append(a);b.max_height=Math.max(b.max_height,a.height());b.content_div.css("height",b.max_height+"px");if(a.hasClass(FILTERABLE_CLASS)){show_hide_popupmenu_options(b.popup_menu,"(Show|Hide) filters");if(b.filters_visible){b.filtering_div.show()}}else{show_hide_popupmenu_options(b.popup_menu,"(Show|Hide) filters",false);b.filtering_div.hide()}},set_overview:function(){var a=this.view;if(this.initial_canvas&&this.is_overview){a.overview_close.show();a.overview_viewport.append(this.initial_canvas);a.overview_highlight.show().height(this.initial_canvas.height());a.overview_viewport.height(this.initial_canvas.height()+a.overview_box.height())}$(window).trigger("resize")}});var LabelTrack=function(a,b){this.track_type="LabelTrack";this.hidden=true;Track.call(this,null,a,b);this.container_div.addClass("label-track")};$.extend(LabelTrack.prototype,Track.prototype,{draw:function(){var c=this.view,d=c.high-c.low,g=Math.floor(Math.pow(10,Math.floor(Math.log(d)/Math.log(10)))),a=Math.floor(c.low/g)*g,e=this.content_div.width(),b=$("<div style='position: relative; height: 1.3em;'></div>");while(a<c.high){var f=(a-c.low)/d*e;b.append($("<div class='label'>"+commatize(a)+"</div>").css({position:"absolute",left:f-1}));a+=g}this.content_div.children(":first").remove();this.content_div.append(b)}});var ReferenceTrack=function(a){this.track_type="ReferenceTrack";this.hidden=true;Track.call(this,null,a,a.top_labeltrack);TiledTrack.call(this);this.left_offset=200;this.height_px=12;this.container_div.addClass("reference-track");this.data_queue={};this.data_cache=new Cache(CACHED_DATA);this.tile_cache=new Cache(CACHED_TILES_LINE)};$.extend(ReferenceTrack.prototype,TiledTrack.prototype,{get_data:function(d,b){var c=this,a=b*DENSITY*d,f=(b+1)*DENSITY*d,e=d+"_"+b;if(!c.data_queue[e]){c.data_queue[e]=true;$.ajax({url:reference_url,dataType:"json",data:{chrom:this.view.chrom,low:a,high:f,dbkey:this.view.dbkey},success:function(g){c.data_cache.set(e,g);delete c.data_queue[e];c.draw()},error:function(h,g,i){console.log(h,g,i)}})}},draw_tile:function(f,b,k,o){var g=b*DENSITY*f,d=DENSITY*f,j=f+"_"+b;var e=document.createElement("canvas");if(window.G_vmlCanvasManager){G_vmlCanvasManager.initElement(e)}e=$(e);var n=e.get(0).getContext("2d");if(o>PX_PER_CHAR){if(this.data_cache.get(j)===undefined){this.get_data(f,b);return}var m=this.data_cache.get(j);if(m===null){this.content_div.css("height","0px");return}e.get(0).width=Math.ceil(d*o+this.left_offset);e.get(0).height=this.height_px;e.css({position:"absolute",top:0,left:(g-this.view.low)*o-this.left_offset});for(var h=0,l=m.length;h<l;h++){var a=Math.round(h*o),i=Math.round(o/2);n.fillText(m[h],a+this.left_offset+i,10)}k.append(e);return e}this.content_div.css("height","0px")}});var LineTrack=function(d,b,a,c){this.track_type="LineTrack";this.display_modes=["Histogram","Line","Filled","Intensity"];this.mode="Histogram";Track.call(this,d,b,b.viewport_container);TiledTrack.call(this);this.height_px=80;this.dataset_id=a;this.data_cache=new Cache(CACHED_DATA);this.tile_cache=new Cache(CACHED_TILES_LINE);this.prefs={color:"black",min_value:undefined,max_value:undefined,mode:this.mode}};$.extend(LineTrack.prototype,TiledTrack.prototype,{init:function(){var a=this,b=a.view.tracks.indexOf(a);a.vertical_range=undefined;this.init_each({stats:true,chrom:a.view.chrom,low:null,high:null,dataset_id:a.dataset_id},function(c){a.container_div.addClass("line-track");var e=c.data;if(isNaN(parseFloat(a.prefs.min_value))||isNaN(parseFloat(a.prefs.max_value))){a.prefs.min_value=e.min;a.prefs.max_value=e.max;$("#track_"+b+"_minval").val(a.prefs.min_value);$("#track_"+b+"_maxval").val(a.prefs.max_value)}a.vertical_range=a.prefs.max_value-a.prefs.min_value;a.total_frequency=e.total_frequency;a.container_div.find(".yaxislabel").remove();var f=$("<div />").addClass("yaxislabel").attr("id","linetrack_"+b+"_minval").text(round_1000(a.prefs.min_value));var d=$("<div />").addClass("yaxislabel").attr("id","linetrack_"+b+"_maxval").text(round_1000(a.prefs.max_value));d.css({position:"absolute",top:"24px",left:"10px"});d.prependTo(a.container_div);f.css({position:"absolute",top:a.height_px+12+"px",left:"10px"});f.prependTo(a.container_div)})},get_data:function(d,b){var c=this,a=b*DENSITY*d,f=(b+1)*DENSITY*d,e=d+"_"+b;if(!c.data_queue[e]){c.data_queue[e]=true;$.ajax({url:data_url,dataType:"json",data:{chrom:this.view.chrom,low:a,high:f,dataset_id:this.dataset_id,resolution:this.view.resolution},success:function(g){var h=g.data;c.data_cache.set(e,h);delete c.data_queue[e];c.draw()},error:function(h,g,i){console.log(h,g,i)}})}},draw_tile:function(o,r,c,e){if(this.vertical_range===undefined){return}var s=r*DENSITY*o,a=DENSITY*o,w=o+"_"+r;var b=document.createElement("canvas");if(window.G_vmlCanvasManager){G_vmlCanvasManager.initElement(b)}b=$(b);if(this.data_cache.get(w)===undefined){this.get_data(o,r);return}var v=this.data_cache.get(w);if(!v){return}b.css({position:"absolute",top:0,left:(s-this.view.low)*e});b.get(0).width=Math.ceil(a*e);b.get(0).height=this.height_px;var n=b.get(0).getContext("2d"),j=false,k=this.prefs.min_value,g=this.prefs.max_value,m=this.vertical_range,t=this.total_frequency,d=this.height_px,l=this.mode;n.beginPath();n.fillStyle=this.prefs.color;var u,h,f;if(v.length>1){f=Math.ceil((v[1][0]-v[0][0])*e)}else{f=10}for(var p=0,q=v.length;p<q;p++){u=Math.round((v[p][0]-s)*e);h=v[p][1];if(h===null){if(j&&l==="Filled"){n.lineTo(u,d)}j=false;continue}if(h<k){h=k}else{if(h>g){h=g}}if(l==="Histogram"){h=Math.round(d-(h-k)/m*d);n.fillRect(u,h,f,d-h)}else{if(l==="Intensity"){h=255-Math.floor((h-k)/m*255);n.fillStyle="rgb("+h+","+h+","+h+")";n.fillRect(u,0,f,d)}else{h=Math.round(d-(h-k)/m*d);if(j){n.lineTo(u,h)}else{j=true;if(l==="Filled"){n.moveTo(u,d);n.lineTo(u,h)}else{n.moveTo(u,h)}}}}}if(l==="Filled"){if(j){n.lineTo(u,d)}n.fill()}else{n.stroke()}c.append(b);return b},gen_options:function(m){var a=$("<div />").addClass("form-row");var e="track_"+m+"_color",b=$("<label />").attr("for",e).text("Color:"),c=$("<input />").attr("id",e).attr("name",e).val(this.prefs.color),h="track_"+m+"_minval",l=$("<label></label>").attr("for",h).text("Min value:"),d=(this.prefs.min_value===undefined?"":this.prefs.min_value),k=$("<input></input>").attr("id",h).val(d),j="track_"+m+"_maxval",g=$("<label></label>").attr("for",j).text("Max value:"),i=(this.prefs.max_value===undefined?"":this.prefs.max_value),f=$("<input></input>").attr("id",j).val(i);return a.append(l).append(k).append(g).append(f).append(b).append(c)},update_options:function(d){var a=$("#track_"+d+"_minval").val(),c=$("#track_"+d+"_maxval").val(),b=$("#track_"+d+"_color").val();if(a!==this.prefs.min_value||c!==this.prefs.max_value||b!==this.prefs.color){this.prefs.min_value=parseFloat(a);this.prefs.max_value=parseFloat(c);this.prefs.color=b;this.vertical_range=this.prefs.max_value-this.prefs.min_value;$("#linetrack_"+d+"_minval").text(this.prefs.min_value);$("#linetrack_"+d+"_maxval").text(this.prefs.max_value);this.tile_cache.clear();this.draw()}}});var FeatureTrack=function(d,b,a,e,c){this.track_type="FeatureTrack";this.display_modes=["Auto","Dense","Squish","Pack"];Track.call(this,d,b,b.viewport_container,e);TiledTrack.call(this);this.height_px=0;this.container_div.addClass("feature-track");this.dataset_id=a;this.zo_slots={};this.show_labels_scale=0.001;this.showing_details=false;this.vertical_detail_px=10;this.vertical_nodetail_px=3;this.summary_draw_height=30;this.default_font="9px Monaco, Lucida Console, monospace";this.inc_slots={};this.data_queue={};this.s_e_by_tile={};this.tile_cache=new Cache(CACHED_TILES_FEATURE);this.data_cache=new Cache(20);this.left_offset=200;this.prefs={block_color:"#444",label_color:"black",show_counts:true}};$.extend(FeatureTrack.prototype,TiledTrack.prototype,{init:function(){var a=this,b="initial";this.init_each({low:a.view.max_low,high:a.view.max_high,dataset_id:a.dataset_id,chrom:a.view.chrom,resolution:this.view.resolution,mode:a.mode},function(c){a.mode_div.show();a.data_cache.set(b,c);a.draw()})},get_data:function(a,d){var b=this,c=a+"_"+d;if(!b.data_queue[c]){b.data_queue[c]=true;$.getJSON(data_url,{chrom:b.view.chrom,low:a,high:d,dataset_id:b.dataset_id,resolution:this.view.resolution,mode:this.mode},function(e){b.data_cache.set(c,e);delete b.data_queue[c];b.draw()})}},incremental_slots:function(a,g,b,q){if(!this.inc_slots[a]){this.inc_slots[a]={};this.inc_slots[a].w_scale=a;this.inc_slots[a].mode=q;this.s_e_by_tile[a]={}}var m=this.inc_slots[a].w_scale,y=[],h=0,n=this.view.max_low;var A=[];if(this.inc_slots[a].mode!==q){delete this.inc_slots[a];this.inc_slots[a]={mode:q,w_scale:m};delete this.s_e_by_tile[a];this.s_e_by_tile[a]={}}for(var v=0,w=g.length;v<w;v++){var f=g[v],l=f[0];if(this.inc_slots[a][l]!==undefined){h=Math.max(h,this.inc_slots[a][l]);A.push(this.inc_slots[a][l])}else{y.push(v)}}for(var v=0,w=y.length;v<w;v++){var f=g[y[v]],l=f[0],r=f[1],c=f[2],p=f[3],d=Math.floor((r-n)*m),e=Math.ceil((c-n)*m);if(p!==undefined&&!b){var s=CONTEXT.measureText(p).width;if(d-s<0){e+=s}else{d-=s}}var u=0;while(u<=MAX_FEATURE_DEPTH){var o=true;if(this.s_e_by_tile[a][u]!==undefined){for(var t=0,z=this.s_e_by_tile[a][u].length;t<z;t++){var x=this.s_e_by_tile[a][u][t];if(e>x[0]&&d<x[1]){o=false;break}}}if(o){if(this.s_e_by_tile[a][u]===undefined){this.s_e_by_tile[a][u]=[]}this.s_e_by_tile[a][u].push([d,e]);this.inc_slots[a][l]=u;h=Math.max(h,u);break}u++}}return h},rect_or_text:function(r,l,t,b,q,f,i,e){r.textAlign="center";var k=0,p=Math.round(l/2);for(var m=0,s=i.length;m<s;m++){var j=i[m],d="MIDNSHP"[j[0]],n=j[1];if(d==="H"||d==="S"){k-=n}var g=q+k,w=Math.floor(Math.max(0,(g-t)*l)),h=Math.floor(Math.max(0,(g+n-t)*l));switch(d){case"S":case"H":case"M":var o=f.slice(k,n);if((this.mode==="Pack"||this.mode==="Auto")&&f!==undefined&&l>PX_PER_CHAR){r.fillStyle=this.prefs.block_color;r.fillRect(w+this.left_offset,e+1,h-w,9);r.fillStyle=CONNECTOR_COLOR;for(var u=0,a=o.length;u<a;u++){if(g+u>=t&&g+u<=b){var v=Math.floor(Math.max(0,(g+u-t)*l));r.fillText(o[u],v+this.left_offset+p,e+9)}}}else{r.fillStyle=this.prefs.block_color;r.fillRect(w+this.left_offset,e+4,h-w,3)}break;case"N":r.fillStyle=CONNECTOR_COLOR;r.fillRect(w+this.left_offset,e+5,h-w,1);break;case"D":r.fillStyle="red";r.fillRect(w+this.left_offset,e+4,h-w,3);break;case"P":case"I":break}k+=n}},draw_tile:function(ag,o,s,av){var N=o*DENSITY*ag,al=(o+1)*DENSITY*ag,M=al-N;var an=(!this.initial_canvas?"initial":N+"_"+al);var I=this.data_cache.get(an);var e;if(I===undefined||(this.mode!=="Auto"&&I.dataset_type==="summary_tree")){this.data_queue[[N,al]]=true;this.get_data(N,al);return}var a=Math.ceil(M*av),ai=this.prefs.label_color,l=this.prefs.block_color,r=this.mode,z=25,ae=(r==="Squish")||(r==="Dense")&&(r!=="Pack")||(r==="Auto"&&(I.extra_info==="no_detail")),W=this.left_offset,au,D,aw;var q=document.createElement("canvas");if(window.G_vmlCanvasManager){G_vmlCanvasManager.initElement(q)}q=$(q);if(I.dataset_type==="summary_tree"){D=this.summary_draw_height}else{if(r==="Dense"){D=z;aw=10}else{aw=(ae?this.vertical_nodetail_px:this.vertical_detail_px);var A=(av<0.0001?1/this.view.zoom_res:av);D=this.incremental_slots(A,I.data,ae,r)*aw+z;au=this.inc_slots[A]}}q.css({position:"absolute",top:0,left:(N-this.view.low)*av-W});q.get(0).width=a+W;q.get(0).height=D;s.parent().css("height",Math.max(this.height_px,D)+"px");var J=q.get(0).getContext("2d");J.fillStyle=l;J.font=this.default_font;J.textAlign="right";this.container_div.find(".yaxislabel").remove();if(I.dataset_type=="summary_tree"){var Y=I.data,L=I.max,b=Math.ceil(I.delta*av);var p=$("<div />").addClass("yaxislabel").text(L);p.css({position:"absolute",top:"22px",left:"10px"});p.prependTo(this.container_div);for(var ap=0,H=Y.length;ap<H;ap++){var aa=Math.floor((Y[ap][0]-N)*av);var Z=Y[ap][1];if(!Z){continue}var am=Z/L*this.summary_draw_height;J.fillStyle="black";J.fillRect(aa+W,this.summary_draw_height-am,b,am);if(this.prefs.show_counts&&J.measureText(Z).width<b){J.fillStyle="#bbb";J.textAlign="center";J.fillText(Z,aa+W+(b/2),this.summary_draw_height-5)}}e="Summary";s.append(q);return q}if(I.message){q.css({border:"solid red","border-width":"2px 2px 2px 0px"});J.fillStyle="red";J.textAlign="left";J.fillText(I.message,100+W,aw)}var ad=false;if(I.data){ad=true;for(var ar=0;ar<this.filters.length;ar++){if(!this.filters[ar].applies_to(I.data[0])){ad=false}}}if(ad){q.addClass(FILTERABLE_CLASS)}var at=I.data;var ao=0;for(var ap=0,H=at.length;ap<H;ap++){var S=at[ap],R=S[0],aq=S[1],ac=S[2],O=S[3];if(au[R]===undefined){continue}var ab=false;var U;for(var ar=0;ar<this.filters.length;ar++){U=this.filters[ar];U.update_attrs(S);if(!U.keep(S)){ab=true;break}}if(ab){continue}if(aq<=al&&ac>=N){var af=Math.floor(Math.max(0,(aq-N)*av)),K=Math.ceil(Math.min(a,Math.max(0,(ac-N)*av))),X=(r==="Dense"?1:(1+au[R]))*aw;var G,aj,P=null,ax=null;if(I.dataset_type==="bai"){var v=S[4];J.fillStyle=l;if(S[5] instanceof Array){var E=Math.floor(Math.max(0,(S[5][0]-N)*av)),Q=Math.ceil(Math.min(a,Math.max(0,(S[5][1]-N)*av))),C=Math.floor(Math.max(0,(S[6][0]-N)*av)),w=Math.ceil(Math.min(a,Math.max(0,(S[6][1]-N)*av)));if(S[5][1]>=N&&S[5][0]<=al){this.rect_or_text(J,av,N,al,S[5][0],S[5][2],v,X)}if(S[6][1]>=N&&S[6][0]<=al){this.rect_or_text(J,av,N,al,S[6][0],S[6][2],v,X)}if(C>Q){J.fillStyle=CONNECTOR_COLOR;J.fillRect(Q+W,X+5,C-Q,1)}}else{J.fillStyle=l;this.rect_or_text(J,av,N,al,aq,O,v,X)}if(r!=="Dense"&&!ae&&aq>N){J.fillStyle=this.prefs.label_color;if(o===0&&af-J.measureText(O).width<0){J.textAlign="left";J.fillText(R,K+2+W,X+8)}else{J.textAlign="right";J.fillText(R,af-2+W,X+8)}J.fillStyle=l}}else{if(I.dataset_type==="interval_index"){if(ae){J.fillStyle=l;J.fillRect(af+W,X+5,K-af,1)}else{var F=S[4],V=S[5],ah=S[6],h=S[7];if(V&&ah){P=Math.floor(Math.max(0,(V-N)*av));ax=Math.ceil(Math.min(a,Math.max(0,(ah-N)*av)))}if(r!=="Dense"&&O!==undefined&&aq>N){J.fillStyle=ai;if(o===0&&af-J.measureText(O).width<0){J.textAlign="left";J.fillText(O,K+2+W,X+8)}else{J.textAlign="right";J.fillText(O,af-2+W,X+8)}J.fillStyle=l}if(h){if(F){if(F=="+"){J.fillStyle=RIGHT_STRAND}else{if(F=="-"){J.fillStyle=LEFT_STRAND}}J.fillRect(af+W,X,K-af,10);J.fillStyle=l}for(var an=0,g=h.length;an<g;an++){var u=h[an],d=Math.floor(Math.max(0,(u[0]-N)*av)),T=Math.ceil(Math.min(a,Math.max((u[1]-N)*av)));if(d>T){continue}G=5;aj=3;J.fillRect(d+W,X+aj,T-d,G);if(P!==undefined&&!(d>ax||T<P)){G=9;aj=1;var ak=Math.max(d,P),B=Math.min(T,ax);J.fillRect(ak+W,X+aj,B-ak,G)}}}else{G=9;aj=1;J.fillRect(af+W,X+aj,K-af,G);if(S.strand){if(S.strand=="+"){J.fillStyle=RIGHT_STRAND_INV}else{if(S.strand=="-"){J.fillStyle=LEFT_STRAND_INV}}J.fillRect(af+W,X,K-af,10);J.fillStyle=l}}}}else{if(I.dataset_type==="vcf"){if(ae){J.fillStyle=l;J.fillRect(af+W,X+5,K-af,1)}else{var t=S[4],n=S[5],c=S[6];G=9;aj=1;J.fillRect(af+W,X,K-af,G);if(r!=="Dense"&&O!==undefined&&aq>N){J.fillStyle=ai;if(o===0&&af-J.measureText(O).width<0){J.textAlign="left";J.fillText(O,K+2+W,X+8)}else{J.textAlign="right";J.fillText(O,af-2+W,X+8)}J.fillStyle=l}var m=t+" / "+n;if(aq>N&&J.measureText(m).width<(K-af)){J.fillStyle="white";J.textAlign="center";J.fillText(m,W+af+(K-af)/2,X+8);J.fillStyle=l}}}}}ao++}}return q},gen_options:function(i){var a=$("<div />").addClass("form-row");var e="track_"+i+"_block_color",k=$("<label />").attr("for",e).text("Block color:"),l=$("<input />").attr("id",e).attr("name",e).val(this.prefs.block_color),j="track_"+i+"_label_color",g=$("<label />").attr("for",j).text("Text color:"),h=$("<input />").attr("id",j).attr("name",j).val(this.prefs.label_color),f="track_"+i+"_show_count",c=$("<label />").attr("for",f).text("Show summary counts"),b=$('<input type="checkbox" style="float:left;"></input>').attr("id",f).attr("name",f).attr("checked",this.prefs.show_counts),d=$("<div />").append(b).append(c);return a.append(k).append(l).append(g).append(h).append(d)},update_options:function(d){var b=$("#track_"+d+"_block_color").val(),c=$("#track_"+d+"_label_color").val(),a=$("#track_"+d+"_show_count").attr("checked");if(b!==this.prefs.block_color||c!==this.prefs.label_color||a!==this.prefs.show_counts){this.prefs.block_color=b;this.prefs.label_color=c;this.prefs.show_counts=a;this.tile_cache.clear();this.draw()}}});var ReadTrack=function(d,b,a,e,c){FeatureTrack.call(this,d,b,a,e,c);this.track_type="ReadTrack";this.vertical_detail_px=10;this.vertical_nodetail_px=5};$.extend(ReadTrack.prototype,TiledTrack.prototype,FeatureTrack.prototype,{});