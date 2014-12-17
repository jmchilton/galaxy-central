<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy.tools import Tool, ToolSection %>

<script type="text/javascript">
$().ready(function() {
%if tool_id:
    var focus_el = $("input[name=reload_tool_button]");
%else:
    var focus_el = $("select[name=tool_id]");
%endif
    focus_el.focus();
});
</script>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Reload Tool</div>
    <div class="toolFormBody">
    <form name="reload_tool" id="reload_tool" action="${h.url_for( controller='admin', action='reload_tool' )}" method="post" >
        <div class="form-row">
            <label>
                Tool to reload:
            </label>
            <select name="tool_id">
                %for key, val in toolbox.tool_panel.items():
                    %if isinstance( val, Tool ):
                        <option value="${val.id}">${val.name|h}</option>
                    %elif isinstance( val, ToolSection ):
                        <optgroup label="${val.name|h}">
                        <% section = val %>
                        %for section_key, section_val in section.elems.items():
                            %if isinstance( section_val, Tool ):
                                <% selected_str = "" %>
                                %if section_val.id == tool_id:
                                     <% selected_str = " selected=\"selected\"" %>
                                %endif
                                <option value="${section_val.id}"${selected_str}>${section_val.name|h}</option>
                            %endif
                        %endfor
                    %endif
                %endfor
            </select>
        </div>
        <div class="form-row">
            <input type="submit" name="reload_tool_button" value="Reload"/>
        </div>
    </form>
    </div>
</div>
