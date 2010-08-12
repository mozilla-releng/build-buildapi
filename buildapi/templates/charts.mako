<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>Charts Test Page</title>
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
    google.load('visualization', '1', {'packages':['corechart']});
    google.setOnLoadCallback(initialize);

    function initialize() {
        var data_url = updateUrlParams({format:'chart', num: 'ptg'});
        var query = new google.visualization.Query(data_url);
        query.send(handleQueryResponse_WaitTimesPercentage);

        ${c.jscode_data}
        drawColumnChart(document.getElementById('stacked_column_chart_full_div'), jscode_data, true, 'Wait Times - Column Chart Job Numbers Stacked');
        drawColumnChart(document.getElementById('column_chart_full_div'), jscode_data, false, 'Wait Times - Column Chart Job Numbers');
        drawAreaChart(document.getElementById('stacked_area_chart_full_div'), jscode_data, true, 'Wait Times - Area Chart Job Numbers Stacked');
        drawAreaChart(document.getElementById('area_chart_full_div'), jscode_data, false, 'Wait Times - Area Chart Job Numbers');
        drawLineChart(document.getElementById('line_chart_full_div'), jscode_data, false, 'Wait Times - Line Chart Job Numbers');
    }

    function handleQueryResponse_WaitTimesFull(response) {
        if (response.isError()) {
            console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
            return;
        }

        var data = response.getDataTable();
        drawColumnChart(document.getElementById('column_chart_div'), data, true);
    }

    function handleQueryResponse_WaitTimesPercentage(response) {
        if (response.isError()) {
            console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
            return;
        }

        var data = response.getDataTable();
        drawAreaChart(document.getElementById('stacked_area_chart_div'), data, true, 'Wait Times - Area Chart Percentage Stacked');
        drawAreaChart(document.getElementById('area_chart_div'), data, false, 'Wait Times - Area Chart Percentage');
    }

    $(document).ready(function() {
        $("#starttime, #endtime").AnyTime_picker({ format: AnyTime_picker_format });
        $("#timeIntervalButton").click(updateWindowLocation);

        initAnyTimePickers();	
    });
</script>
</head>
<body id="dt_example">
<h1>Charts</h1>

<div>
<p>Build pool: 
% if c.pool == 'buildpool':
    <b>buildpool</b> |
% else:
    <a href="${url.current(pool='buildpool', **dict(request.params))}">buildpool</a> |
% endif
% if c.pool == 'trybuildpool':
    <b>trybuildpool</b> |
% else:
    <a href="${url.current(pool='trybuildpool', **dict(request.params))}">trybuildpool</a> |
% endif
% if c.pool == 'testpool':
    <b>testpool</b>
% else:
    <a href="${url.current(pool='testpool', **dict(request.params))}">testpool</a>
% endif
</p><p>
<label for="starttime">Jobs submitted between</label>
<input type="text" id="starttime" size="26" value="" ref="${c.starttime}"/>
<label for="endtime2">and</label>
<input type="text" id="endtime" size="26" value="" ref="${c.endtime}"/>
<input type="button" id="timeIntervalButton" value="Go!"/>
<a href="">&lt;&lt;Previous</a> | <a href="">Next&gt;&gt;</a>
</p><br/>
</div>
<div>
<div>Wait time report for <b>${c.pool}</b> for jobs submitted between <b>${h.pacific_time(c.starttime)}</b> and <b>${h.pacific_time(c.endtime)}</b></div>

<h2>Area Charts</h2>
<div id="stacked_area_chart_div"></div>
<div id="area_chart_div"></div>
<div id="stacked_area_chart_full_div"></div>
<div id="area_chart_full_div"></div>

<h2>Column Charts</h2>
<div id="stacked_column_chart_full_div"></div>
<dif id="column_chart_full_div"></div>

<h2>Line Charts</h2>
<div id="line_chart_full_div"></div>

<br/>Generated at ${h.pacific_time(None)}.
</body>
</html>
