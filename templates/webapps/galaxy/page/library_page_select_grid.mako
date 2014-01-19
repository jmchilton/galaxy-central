<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="shared"
    self.message_box_visible=False
%>
</%def>

<%def name="title()">
    Collaborate using Libraries
</%def>
<%def name="center_panel()">
<h2 style="text-indent:20px"></h2>
<h2 style="text-indent:20px">Publish these pages to the selected libraries</h2>
<br>
<p style="text-indent:100px">
${pagetitles}
</p>
<br>

<h2 style="text-indent:30px">Selected libraries (if none are selected, pages will be disconnected from all libraries)</h2>

    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            ${ grid( trans, url_extra=url_extra ) }
        </div>
    </div>

</%def>
