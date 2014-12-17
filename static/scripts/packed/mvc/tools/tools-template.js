define([],function(){return{help:function(a){return'<div class="toolHelp"><div class="toolHelpBody">'+a+"</div></div>"},success:function(c){if(!c.jobs||!c.jobs.length){console.debug("tools-template::success() - Failed jobs.");return}var a=c.jobs.length;var d="";if(a==1){d="1 job has"}else{d=a+" jobs have"}var b='<div class="donemessagelarge"><p>'+d+" been successfully added to the queue - resulting in the following datasets:</p>";for(var e in c.outputs){b+='<p style="padding: 10px 20px;"><b>'+(parseInt(e)+1)+": "+c.outputs[e].name+"</b></p>"}b+="<p>You can check the status of queued jobs and view the resulting data by refreshing the History pane. When the job has been run the status will change from 'running' to 'finished' if completed successfully or 'error' if problems were encountered.</p></div>";return b},error:function(a){return'<div><p>The server could not complete the request. Please contact the Galaxy Team if this error persists.</p><textarea class="ui-textarea" disabled style="color: black;" rows="6">'+JSON.stringify(a,undefined,4)+"</textarea></div>"},batchMode:function(){return'<div class="ui-table-form-info"><i class="fa fa-sitemap" style="font-size: 1.2em; padding: 2px 5px;"/>This is a batch mode input field. A separate job will be triggered for each dataset.</div>'},requirements:function(a){var d="This tool requires ";for(var b in a.requirements){var c=a.requirements[b];d+=c.name;if(c.version){d+=" (Version "+c.version+")"}if(b<a.requirements.length-2){d+=", "}if(b==a.requirements.length-2){d+=" and "}}return d+'. Click <a target="_blank" href="https://wiki.galaxyproject.org/Tools/Requirements">here</a> for more information.'}}});