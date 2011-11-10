<%inherit file="/base.mako" />
<%def name="title()">Builds for ${c.branch}</%def>
<%def name="header()">
<script type="text/javascript">
function revurl(rev)
{
    return "${h.url('branch', branch=c.branch)}/rev/" + rev;
}

$(document).ready(function()
{
    var options = {
        bJQueryUI: true,
        sPaginationType: "full_numbers"
    }
    $("#builds").dataTable(options);
    $("#running").dataTable(options);
    $("#pending").dataTable(options);

    $("#revform").submit(function()
    {
        var rev = $("#revfield").val();
        $(location).attr('href', revurl(rev));
        return false;
    });

    $("#newbuildform").submit(function()
    {
        var rev = $("#newbuildform input[name=revision]").val();
        $("#newbuildform").attr('action', revurl(rev));
        return true;
    });
    $("#newpgobuildform").submit(function()
    {
        var rev = $("#newpgobuildform input[name=revision]").val();
        $("#newpgobuildform").attr('action', revurl(rev) + '/pgo');
        return true;
    });
    $("#newnightlyform").submit(function()
    {
        var rev = $("#newnightlyform input[name=revision]").val();
        $("#newnightlyform").attr('action', revurl(rev) + '/nightly');
        return true;
    });
})

function toggle_display(id)
{
    var node = $(id);
    if (node.css('display') == 'none')
    {
        node.css('display', 'inline');
    }
    else
    {
        node.css('display', 'none');
    }
}
</script>
</%def>

<%def name="cancel_request_form(request_id)">
<form method="POST" action="${h.url('cancel_request', branch=c.branch, request_id=request_id)}">
<input type="hidden" name="_method" value="DELETE" />
<input type="submit" value="cancel" />
</form>
</%def>

<%def name="cancel_build_form(build_id)">
<form method="POST" action="${h.url('cancel_build', branch=c.branch, build_id=build_id)}">
<input type="hidden" name="_method" value="DELETE" />
<input type="submit" value="cancel" />
</form>
</%def>

<%def name="rebuild_form(build_id)">
<form method="POST" action="${h.url('rebuild_build', branch=c.branch)}">
<input type="hidden" name="_method" value="POST" />
<input type="hidden" name="build_id" value="${build_id}" />
<input type="submit" value="rebuild" />
</form>
</%def>

<%def name="priority_form(request_id, priority, label)">
<form method="POST" action="${h.url('reprioritize', branch=c.branch, request_id=request_id)}">
<input type="hidden" name="_method" value="PUT" />
<input type="hidden" name="priority" value="${priority}" />
<input type="submit" value="${label}" />
</form>
</%def>
<%def name="buildrow(build, tabletype)">
<tr class="result${build.get('status')}">
    <td>
    % if tabletype in ('running', 'pending'):
        % if build.get('build_id'):
            ${cancel_build_form(build['build_id'])}
        % elif build.get('request_id'):
            ${cancel_request_form(build['request_id'])}
        % endif
    % endif
    % if build.get('build_id'):
        ${rebuild_form(build['build_id'])}
    % endif
    </td>
    % if build.get('build_id'):
        <td><a href="${h.url('build', branch=c.branch, build_id=build.get('build_id'))}">${build['buildername']}</a></td>
    % elif build.get('request_id'):
        <td><a href="${h.url('request', branch=c.branch, request_id=build.get('request_id'))}">${build['buildername']}</a></td>
    % else:
        <td>${build['buildername']}</td>
    % endif
    <td>
    % if build.get('revision'):
        <a href="${h.url('revision', branch=c.branch, revision=build['revision'])}">${build['revision']}</a>
    % endif
    </td>
    % if tabletype == 'builds':
        <td>${self.attr.formatStatus(build.get('status'))}</td>
    % endif
    % if tabletype == 'pending':
        <td>${self.attr.formattime(build.get('submittime'))}</td>
        <td>${build.get('priority')}
            ${priority_form(build['request_id'], build.get('priority', 0)+1, '+1')}
            ${priority_form(build['request_id'], build.get('priority', 0)-1, '-1')}
        </td>
    % else:
        <td>${self.attr.formattime(build.get('starttime'))}</td>
        <td>${self.attr.formattime(build.get('endtime'))}</td>
    % endif
</tr>
</%def>

<%def name="breadcrumbs()">
<a href="${h.url('selfserve_home')}">BuildAPI Home</a><br/>
</%def>

<%def name="body()">
<form id="revform">
Look up builds by revision: <input id="revfield" type="text" name="revision">
</form>

% if hasattr(c, 'date'):
<%
before = (c.date - self.attr.oneday).strftime('%Y-%m-%d')
after = (c.date + self.attr.oneday).strftime('%Y-%m-%d')
today = c.today.strftime('%Y-%m-%d')
%>
Builds for ${c.branch} on ${c.date.strftime('%Y-%m-%d')}
<a href="${h.url.current(date=before)}">Earlier</a>
<a href="${h.url.current(date=today)}">Today</a>
<a href="${h.url.current(date=after)}">Later</a>
% endif

<%
builds = {'pending': [], 'running': [], 'builds': []}

for b in c.data:
    if not 'starttime' in b or not b['starttime']:
        builds['pending'].append(b)
    elif not b['endtime']:
        builds['running'].append(b)
    else:
        builds['builds'].append(b)
%>

% for tabletype in ('pending', 'running', 'builds'):
    % if not builds[tabletype]:
    <h1>no ${tabletype}</h1>
    <% continue %>
    % endif
    <h1>${tabletype}</h1>
    <div>
    <table id="${tabletype}">
    <thead>
    <tr>
    % if tabletype == 'pending':
        <th></th><th>Builder</th><th>Revision</th><th>Submit time</th><th>Priority</th>
    % elif tabletype == 'running':
        <th></th><th>Builder</th><th>Revision</th><th>Start time</th><th>End time</th>
    % else:
        <th></th><th>Builder</th><th>Revision</th><th>Status</th><th>Start time</th><th>End time</th>
    % endif
    </tr>
    </thead>
    <tbody>
    % for build in builds[tabletype]:
        ${buildrow(build, tabletype)}
    % endfor
    </tbody>
    </table>
    </div>
% endfor

<h1>Create a new build</h1>
<form method="POST" id="newbuildform">
Create new dep builds on ${c.branch} revision <input type="text" name="revision" /> <input type="submit" value="Submit" />
</form>
<form method="POST" id="newpgobuildform">
Create new PGO builds on ${c.branch} revision <input type="text" name="revision" /> <input type="submit" value="Submit" />
</form>
<form method="POST" id="newnightlyform">
Create new nightly builds on ${c.branch} revision <input type="text" name="revision" /> <input type="submit" value="Submit" />
</form>
</%def>
