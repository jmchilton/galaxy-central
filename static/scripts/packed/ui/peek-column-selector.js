(function(a){if(typeof define==="function"&&define.amd){define(["jquery"],a)}else{a(jQuery)}}(function(b){var f={renameColumns:false,columnNames:[],commentChar:"#",hideCommentRows:false,includePrompts:true,topLeftContent:"Columns:"},m="peek-column-selector",t="peek-column-selector.change",u="peek-column-selector.rename",w="control",e="control-prompt",c="selected",o="disabled",v="button",r="renamable-header",q="column-index",a="column-name";function i(x){if(x.disabled&&jQuery.type(x.disabled)!=="array"){throw new Error('"disabled" must be defined as an array of indeces: '+JSON.stringify(x))}if(x.multiselect&&x.selected&&jQuery.type(x.selected)!=="array"){throw new Error('Mulitselect rows need an array for "selected": '+JSON.stringify(x))}if(!x.label||!x.id){throw new Error("Peek controls need a label and id for each control row: "+JSON.stringify(x))}if(x.disabled&&x.disabled.indexOf(x.selected)!==-1){throw new Error("Selected column is in the list of disabled columns: "+JSON.stringify(x))}return x}function p(y,x){return b("<div/>").addClass(v).text(y.label)}function l(y,x){var z=b("<td/>").html(p(y,x)).attr("data-"+q,x);if(y.disabled&&y.disabled.indexOf(x)!==-1){z.addClass(o)}return z}function d(z,A,x){var y=z.children("."+v);if(z.hasClass(c)){y.html((A.selectedText!==undefined)?(A.selectedText):(A.label))}else{y.html((A.unselectedText!==undefined)?(A.unselectedText):(A.label))}}function h(A,y){var z=l(A,y);if(A.selected===y){z.addClass(c)}d(z,A,y);if(!z.hasClass(o)){z.click(function x(E){var F=b(this);if(!F.hasClass(c)){var B=F.parent().children("."+c).removeClass(c);B.each(function(){d(b(this),A,y)});F.addClass(c);d(F,A,y);var D={},C=F.parent().attr("id"),G=F.data(q);D[C]=G;F.parents(".peek").trigger(t,D)}})}return z}function n(A,y){var z=l(A,y);if(A.selected&&A.selected.indexOf(y)!==-1){z.addClass(c)}d(z,A,y);if(!z.hasClass(o)){z.click(function x(E){var F=b(this);F.toggleClass(c);d(F,A,y);var D=F.parent().find("."+c).map(function(H,I){return b(I).data(q)});var C={},B=F.parent().attr("id"),G=jQuery.makeArray(D);C[B]=G;F.parents(".peek").trigger(t,C)})}return z}function k(z,A){var x=[];for(var y=0;y<z;y+=1){x.push(A.multiselect?n(A,y):h(A,y))}return x}function s(z,A,y){var B=b("<tr/>").attr("id",A.id).addClass(w);if(y){var x=b("<td/>").addClass(e).text(A.label+":");B.append(x)}B.append(k(z,A));return B}function j(F){F=jQuery.extend(true,{},f,F);var E=b(this).addClass(m),B=E.find("table"),A=B.find("th").size(),D=B.find("tr").size(),x=B.find("td[colspan]").map(function(I,G){var H=b(this);if(H.text()&&H.text().match(new RegExp("^"+F.commentChar))){return b(this).css("color","grey").parent().get(0)}return null});if(F.hideCommentRows){x.hide();D-=x.size()}if(F.includePrompts){var z=b("<th/>").addClass("top-left").text(F.topLeftContent).attr("rowspan",D);B.find("tr").first().prepend(z)}var C=B.find("th:not(.top-left)").each(function(H,J){var I=b(this),K=I.text().replace(/^\d+\.*/,""),G=F.columnNames[H]||K;I.attr("data-"+a,G).text((H+1)+((G)?("."+G):("")))});if(F.renameColumns){C.addClass(r).click(function y(){var H=b(this),G=H.index()+(F.includePrompts?0:1),J=H.data(a),I=prompt("New column name:",J);if(I!==null&&I!==J){H.text(G+(I?("."+I):"")).data(a,I).attr("data-",a,I);var K=jQuery.makeArray(H.parent().children("th:not(.top-left)").map(function(){return b(this).data(a)}));H.parents(".peek").trigger(u,K)}})}F.controls.forEach(function(H,G){i(H);var I=s(A,H,F.includePrompts);B.find("tbody").append(I)});return this}jQuery.fn.extend({peekColumnSelector:function g(x){return this.map(function(){return j.call(this,x)})}})}));