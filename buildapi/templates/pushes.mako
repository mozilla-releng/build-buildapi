<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>List of recent builds</title>
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
<script type="text/javascript">
$(document).ready(function() {
    $("#pending").dataTable({
        "bJQueryUI": true,
        "iDisplayLength": 25,
        "sPaginationType": "full_numbers",
        "aaSorting": [[1,'desc'],[0,'asc']],
      } );
});

</script>
</head>

<body>
<%
  from datetime import datetime
  now = datetime.now().replace(microsecond=0)
%>
Pushes to
% if c.push_limits['branch']:
the repositories matching ${c.push_limits['branch']}*
% else:
all repositories
% endif
% if c.push_limits['fromtime']:
  % if c.push_limits['totime']:
    between ${datetime.fromtimestamp(c.push_limits['fromtime'])} and ${datetime.fromtimestamp(c.push_limits['totime'])}.
  % else:
    after ${datetime.fromtimestamp(c.push_limits['fromtime'])}.
  % endif
% endif

<div class="demo_jui">
<table id="pending" cellpadding="0" cellspacing="0" border="0" class="display">
<thead>
<tr>
% for key in ('Author','Push count'):
<th>${key}</th>
% endfor
</tr></thead><tbody>
% for author in c.pushes:
  <tr> <td>${author}</td><td>${c.pushes[author]}</td> </tr>
%endfor
</tbody><table>

</body>
</html>
Generated at ${now}. All times are Mountain View, CA (US/Pacific).
