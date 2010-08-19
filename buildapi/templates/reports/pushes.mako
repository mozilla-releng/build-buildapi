<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>Pushes Reports</title>
${h.tags.javascript_link(
    url('/jquery/js/jquery-1.4.2.min.js'),
    url('/jquery/js/jquery-ui-1.8.1.custom.min.js'),
    url('/dataTables-1.6/media/js/jquery.dataTables.min.js'),
    url('/anytime/anytime.js'),
    url('/anytime/anytimetz.js'),
    url('/scripts.js'),
    url('/gviz.js'),
    )}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/dataTables-1.6/media/css/demo_page.css')}";
@import "${url('/dataTables-1.6/media/css/demo_table_jui.css')}";
@import "${url('/anytime/anytime.css')}";
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
        data_no_totals.removeColumn(1);

        drawLineChart(document.getElementById('line_chart_div'), data, false);
        drawColumnChart(document.getElementById('column_chart_div'), data_no_totals, true);
        drawBarChart(document.getElementById('bar_chart_div'), data_no_totals, true, '', 600, 600);
    }

    $(document).ready(function() {
        $(".pushes-overall").dataTable({
            "bFilter": false,
            "bAutoWidth": false,
            "bPaginate": false,
            "bInfo": false,
        } );
        $("#starttime, #endtime").AnyTime_picker({ format: AnyTime_picker_format });
        $("#timeIntervalButton").click(updateWindowLocation);

        initAnyTimePickers();
    });
</script>
</head>

<% import time %>
<body id="dt_example">
<h1>Pushes</h1>

<div>
<label for="starttime">Pushes submitted between</label>
<input type="text" id="starttime" size="26" value="" ref="${c.report.starttime}"/>
<label for="endtime2">and</label>
<input type="text" id="endtime" size="26" value="" ref="${c.report.endtime}"/>
<input type="button" id="timeIntervalButton" value="Go!"/>
</p><br/>
</div>
<div>
<br/><div>Pushes report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></div>

<div>
<table class="display pushes-overall" cellpadding="0" cellspacing="0" border="0">
<thead><tr>
  <th>Branch</th><th>Totals</th>
  % for int_idx in range(c.report.int_no):
    <th>${h.pacific_time(c.report.get_interval_timestamp(int_idx), format='%m/%d %H:%M:%S')}</th>
  % endfor
</tr></thead>
<tbody>
<tr class="gradeA">
<td> Totals</td><td>${c.report.total}</td>
% for val in c.report.get_intervals():
  <td>${val}</td>
% endfor
</tr>
% for branch in sorted(c.report.branches):
  <tr>
    <td>${branch}</td><td style="background-color:#EEFFEE">${c.report.get_total(branch=branch)}</td>
    % for val in c.report.get_intervals(branch=branch):
      <td>${val}</td>
    % endfor
  </tr>
% endfor
</tbody></table>
</div>

<div id="table_div"></div>
<div id="line_chart_div"></div>
<div id="column_chart_div"></div>
<div id="bar_chart_div"></div>

<br/>Generated at ${h.pacific_time(None)}.
</body>
</html>
