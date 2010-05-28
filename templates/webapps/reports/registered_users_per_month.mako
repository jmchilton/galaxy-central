<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">User Registrations Per Month</h3>
        <h4 align="center">Click Month to view the number of user registrations for each day of that month</h4>
        <table align="center" width="30%" class="colored">
            %if len( users ) == 0:
                <tr><td colspan="2">There are no registered users</td></tr>
            %else:
                <tr class="header">
                    <td>Month</td>
                    <td>Number of Registrations</td>
                </tr>
                <% ctr = 0 %>
                %for user in users:
                    %if ctr % 2 == 1:
                        <tr class="odd_row">
                    %else:
                        <tr class="tr">
                    %endif
                        <td><a href="${h.url_for( controller='users', action='specified_month', month=user[0], month_label=user[2].strip(), year_label=user[3] )}">${user[2]}&nbsp;${user[3]}</a></td>
                        <td>${user[1]}</td>
                    </tr>
                    <% ctr += 1 %>
                %endfor
            %endif
        </table>
    </div>
</div>
