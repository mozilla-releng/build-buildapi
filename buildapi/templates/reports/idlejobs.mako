<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>Idle Jobs Report</title>
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
<script type="text/javascript" src="//www.google.com/jsapi"></script>
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
        var data_util = jQuery.extend(true, {}, data);

        var cc = new google.visualization.AreaChart(document.getElementById('column_chart_div'));
        google.visualization.events.addListener(cc, 'ready', function() {
            google.visualization.events.addListener(cc, 'ready', function() {
               cc.setSelection(cc.getSelection());
            });
        });
        cc.draw(data_util, {
            title: 'Idle Runs Utilization',
            isStacked: true,
            width: 1500,
            height: 500,
        });
    }

    $(document).ready(function() {
        $(".idlejobs-overall").dataTable({
            "bFilter": true,
            "bAutoWidth": false,
            "bPaginate": false,
            "bInfo": false,
        } );
    });
</script>
</head>

<% import time %>
<%namespace file="util.mako" import="datepicker_menu"/>
<body id="dt_example">
<h1>Idle Jobs</h1>

<div>
<p>
${datepicker_menu(c.idlejobs.starttime, c.idlejobs.endtime)}
</p>
</div>
<div>
<br/><div>Idle Jobs run report for jobs started between <b>${h.pacific_time(c.idlejobs.starttime)}</b> and <b>${h.pacific_time(c.idlejobs.endtime)}</b></div>

<div>
<table class="display idlejobs-overall" cellpadding="0" cellspacing="0" border="0">
<thead><tr>
  <th>Builder</th>
  <th>Total Compute Time spent(over time period)</th>
% for i in range(c.idlejobs.int_no):
      <th>${time.strftime('%m/%d %H:%M', time.localtime(c.idlejobs.get_interval_timestamp(i)))}</th>
% endfor
</tr></thead>
<tbody>
% for builder in c.idlejobs.builders:
  <tr>
    <td>${builder}</td>
        <td>${h.strf_YmdhMs(c.idlejobs.totals[builder])}</td>
%   for i in range(c.idlejobs.int_no):
        <td>${c.idlejobs.builder_intervals[builder][i]}</td>
%   endfor
  </tr>
% endfor
  <tr>
    <td>Total</td>
    <td>${h.strf_YmdhMs(c.idlejobs.totals['Total'])}</td>
%   for i in range(c.idlejobs.int_no):
        <td>${c.idlejobs.builder_intervals['Total'][i]}</td>
%   endfor
  </tr>
</tbody></table>
</div>
<div class="clear"></div>
<div id="table_div"></div>
<div id="column_chart_div"></div>

<br/>Generated at ${h.pacific_time(None)}.
</body>
</html>
