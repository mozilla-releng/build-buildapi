<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>Test Run Reports</title>
${h.tags.javascript_link(
    url('/jquery/js/jquery-1.4.2.min.js'),
    url('/jquery/js/jquery-ui-1.8.1.custom.min.js'),
    url('/DataTables-1.7.1/media/js/jquery.dataTables.min.js'),
    url('/scripts.js'),
    url('/gviz.js'),
    )}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_page.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_table_jui.css')}";
@import "${url('/build-status.css')}";
</style>
<script type="text/javascript" src="http://www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart', 'table']});
    google.setOnLoadCallback(initialize);

    function initialize() {
        var data_url = updateUrlParams({format:'chart'});
        var query = new google.visualization.Query(data_url);
        query.send(handleQueryResponse);
    }

    function handleQueryResponse(response) {
        if (response.isError()) {
           console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
           return;
        }

        var data = response.getDataTable();
        var data_no_totals = jQuery.extend(true, {}, data);

        var cc = new google.visualization.ColumnChart(document.getElementById('column_chart_div'));
        google.visualization.events.addListener(cc, 'ready', function() {
            google.visualization.events.addListener(cc, 'ready', function() {
               cc.setSelection(cc.getSelection());
            });
        });
        cc.draw(data_no_totals, {
            title: 'Test Runs',
            isStacked: true,
            width: 1500,
            height: 500,
        });
    }

    $(document).ready(function() {
        $(".testruns-overall").dataTable({
            "bFilter": true,
            "bAutoWidth": false,
            "bPaginate": true,
            "bInfo": false,
        } );
    });
</script>
</head>

<% import time %>
<body id="dt_example">
<h1>Test Runs</h1>

<div>
<p>Builder Category:
<%
   params = dict(request.params)
   if 'category' in params:
       del params['category']
   if 'platform' in params:
       del params['platform']
   if 'group' in params:
       del params['group']
   if 'btype' in params:
       del params['btype']
   platform = c.testruns.platform if c.testruns.platform != 'ALL' else None
   category = c.testruns.category if c.testruns.category != 'ALL' else None
   btype = c.testruns.btype if c.testruns.btype != 'ALL' else None
   group = c.testruns.group or None
%>
% if c.testruns.category == 'ALL':
    <b>Overall</b> |
% else:
    <a href="${url.current(category=None, platform=platform, group=group, btype=btype, **params)}">Overall</a> |
% endif

% for i in c.testruns.categories:
%     if c.testruns.category == i:
          <b>${i}</b> |
%     else:
          <a href="${url.current(category=i, platform=platform, group=group, btype=btype, **params)}">${i}</a> |
%     endif
% endfor
</p>
<p>Platform:
% if c.testruns.platform == 'ALL':
    <b>Overall</b> |
% else:
    <a href="${url.current(platform=None, category=category, group=group, btype=btype, **params)}">Overall</a> |
% endif

% for i in c.testruns.platforms:
%     if c.testruns.platform == i:
          <b>${i}</b> |
%     else:
          <a href="${url.current(platform=i, category=category, group=group, btype=btype, **params)}">${i}</a> |
%     endif
% endfor
</p><p>Build Type:
% if c.testruns.btype == 'ALL':
    <b>All</b> |
% else:
    <a href="${url.current(platform=platform, category=category, btype=None, group=group, **params)}">All</a> |
% endif

% for i in c.testruns.build_types:
%     if c.testruns.btype == i:
          <b>${i}</b> |
%     else:
          <a href="${url.current(platform=platform, category=category, btype=i, group=group, **params)}">${i}</a> |
%     endif
% endfor

</p><p>Group by Test:
% if c.testruns.group:
      <b>Yes</b> | <a href="${url.current(platform=platform, category=category, btype=btype, **params)}">No</a>
%else:
      <a href="${url.current(platform=platform, category=category, group=True, btype=btype, **params)}">Yes</a> | <b>No</b>
% endif
</p>
<%namespace file="util.mako" import="datepicker_menu"/>
<p>
${datepicker_menu(c.testruns.starttime, c.testruns.endtime)}
</p>
</div>
<div>
<br/><div>Test run report for jobs started between <b>${h.pacific_time(c.testruns.starttime)}</b> and <b>${h.pacific_time(c.testruns.endtime)}</b></div>

<div>
<table class="display testruns-overall" cellpadding="0" cellspacing="0" border="0">
<thead><tr>
  <th>Builder</th>
  <th>Average Total Time for Test Run</th>
  <th>Average Time spent running Tests</th>
  <th>Ratio (Average Test Time / Average Total Time)</th>
</tr></thead>
<tbody>
% for builder in c.testruns.builders:
  <tr>
    <td>${builder}</td>
    <td>${c.testruns.get_total_time(builder=builder)}</td>
    <td>${c.testruns.get_test_time(builder=builder)}</td>
    <td>${c.testruns.get_ratio(builder=builder)}</td>
  </tr>
% endfor
</tbody></table>
</div>

<div id="table_div"></div>
<div id="column_chart_div"></div>

<br/>Generated at ${h.pacific_time(None)}.
</body>
</html>
