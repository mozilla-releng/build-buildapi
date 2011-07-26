<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>List of recent builds</title>
${h.tags.javascript_link(
    url('/jquery/js/jquery-1.4.2.min.js'),
    url('/jquery/js/jquery-ui-1.8.1.custom.min.js'),
    url('/DataTables-1.7.1/media/js/jquery.dataTables.min.js'),
    )}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_page.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_table_jui.css')}";
@import "${url('/build-status.css')}";
</style>
<script type="text/javascript">
$(document).ready(function() {
    $("#pending").dataTable({
        "bJQueryUI": true,
        "iDisplayLength": 25,
        "sPaginationType": "full_numbers",
        "aaSorting": [[5,'desc']],
      } );

});

</script>
</head>

<body>
<div class="demo_jui">
<table id="pending" cellpadding="0" cellspacing="0" border="0" class="display">
<thead>
<tr>
% for key in ('Slave name','Builder name', 'Build number', 'Master', 'Result', 'Start time', 'End time', 'Running time'):
<th>${key}</th>
% endfor
</tr></thead><tbody>
<%
  from pytz import timezone
  from datetime import datetime
  pacific = timezone('US/Pacific')
  utc = timezone('UTC')
  now = datetime.now().replace(microsecond=0)
%>
% for build in c.recent_builds:
  <%
    if build['endtime'] and build['starttime']:
        build['running_for'] = build['endtime'] - build['starttime']
    else:
        build['running_for'] = ""
  %>
  <tr>
  % for key in ('slavename','buildname','buildnumber','master','result','starttime','endtime','running_for'):
    % if 'time' in key and build[key] is not None:
      <td>${build[key].replace(tzinfo=utc).astimezone(pacific).replace(tzinfo=None)}</td>
    % elif key =='result':
      <td class="result${build['result']}">${build[key]}</td>
    % else:
      <td>${build[key]}</td>
    % endif
  % endfor
  </tr>
%endfor
</tbody><table>

</body>
</html>
Generated at ${now}. All times are Mountain View, CA (US/Pacific).
