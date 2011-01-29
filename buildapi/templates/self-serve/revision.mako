<%inherit file="branch.mako" />
<%def name="title()">Builds for ${c.revision} on ${c.branch}</%def>

<%def name="breadcrumbs()">
<a href="${h.url('selfserve_home')}">BuildAPI Home</a> <a href="${h.url('branch', branch=c.branch)}">${c.branch}</a>
</%def>
