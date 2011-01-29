<%inherit file="/base.mako" />
<%!
refresh_interval = 30
%>
<%def name="title()">Job ${c.job_id} status detail</%def>
<%def name="header()">
% if c.data['completed_at'] is None:
<meta http-equiv="refresh" content="${refresh_interval}" />
% endif
</%def>

<%def name="body()">
Job status detail for job ${c.job_id}.
% if c.data['completed_at'] is None:
Will refresh every ${refresh_interval}s.
% endif
<pre>
${c.formatted_data|n}
</pre>
</%def>
