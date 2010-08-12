<%def name="title()">NO TITLE</%def>\
<%def name="footer()">\
<%
    from datetime import datetime
    now = datetime.now().replace(microsecond=0)
%>
Generated at ${now}. All times are Mountain View, CA (US/Pacific).
</%def>\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>${self.title()}</title>
${h.tags.javascript_link(
    url('/jquery/js/jquery-1.4.2.min.js'),
    url('/jquery/js/jquery-ui-1.8.1.custom.min.js'),
    url('/dataTables-1.6/media/js/jquery.dataTables.min.js'),
    )}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/dataTables-1.6/media/css/demo_page.css')}";
@import "${url('/dataTables-1.6/media/css/demo_table_jui.css')}";
</style>
${next.header()}
</head>
<body>
% if c.branches:
    % if len(c.branches) == 1:
        ${h.tags.link_to("Pending Builds for %s" % c.branches[0], url("pending", branch=c.branches[0]))}
        ${h.tags.link_to("Running Builds for %s" % c.branches[0], url("running", branch=c.branches[0]))}
    % else:
        ${h.tags.link_to("Pending Builds for %s" % ",".join(c.branches), url("pending", branch=c.branches))}
        ${h.tags.link_to("Running Builds for %s" % ",".join(c.branches), url("running", branch=c.branches))}
    % endif
% endif
${next.body()}
</body>
${next.footer()}
</html>
