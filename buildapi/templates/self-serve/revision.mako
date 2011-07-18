<%inherit file="branch.mako" />
<%def name="title()">Builds for ${c.revision} on ${c.branch}</%def>
<%def name="header()"></%def>

<%def name="breadcrumbs()">
<a href="${h.url('selfserve_home')}">BuildAPI Home</a> <a href="${h.url('branch', branch=c.branch)}">${c.branch}</a>
</%def>

<%def name="body()">
${parent.body()}
<form method="POST" action="${h.url('cancel_revision', branch=c.branch, revision=c.revision)}">
Cancel all builds on this revision.
<input type="hidden" name="_method" value="DELETE" />
<input type="submit" value="Cancel" />
</form>
</%def>
