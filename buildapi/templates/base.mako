<%def name="title()">NO TITLE</%def>\
<%def name="footer()">\
<%
    from datetime import datetime
    import time
    now = datetime.now().replace(microsecond=0)
    seconds = "%.3g" % (time.time() - c.started)
%>
Generated at ${now} in ${seconds}s. All times are Mountain View, CA (US/Pacific).
</%def>\
<%def name="breadcrumbs()"></%def>\
<%def name="header()"></%def>\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>${self.title()}</title>
${h.tags.javascript_link(
    url('/DataTables-1.7.1/media/js/jquery.js'),
    url('/DataTables-1.7.1/media/js/jquery.dataTables.min.js'),
    )}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/releng.css')}";
@import "${url('/build-status.css')}";
</style>
${next.header()}
</head>
<body>
${self.breadcrumbs()}
${next.body()}
</body>
${next.footer()}
</html>
