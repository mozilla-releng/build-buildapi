<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>Wait times</title>
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
<%
  import time
  wt = c.wait_times
%>
<body id="dt_example">
<h1>Wait Times</h1>
<div>
<p>Build pool: 
<%
  params = request.params.copy()
  if 'pool' in params:
      del params['pool']
%>
% if wt.pool == 'buildpool':
    <b>buildpool</b> |
% else:
    <a href="${url.current(pool='buildpool', **params)}">buildpool</a> |
% endif
% if wt.pool == 'trybuildpool':
    <b>trybuildpool</b> |
% else:
    <a href="${url.current(pool='trybuildpool', **params)}">trybuildpool</a> |
% endif
% if wt.pool == 'testpool':
    <b>testpool</b>
% else:
    <a href="${url.current(pool='testpool', **params)}">testpool</a>
% endif
</p><p>
<label for="starttime">Jobs submitted between</label>
<input type="text" id="starttime" size="26" value="" ref="${wt.starttime}"/>
<label for="endtime2">and</label>
<input type="text" id="endtime" size="26" value="" ref="${wt.endtime}"/>
<input type="button" id="timeIntervalButton" value="Go!"/>
</p><br/>
</div>
<div>
<div>Wait time report for <b>${wt.pool}</b> for jobs submitted between <b>${h.pacific_time(wt.starttime)}</b> 
and <b>${h.pacific_time(wt.endtime)}</b></div>

<div id="wt-stats">
<div class="wt-column-s">

<div class="wt-container">
<h4>Total Jobs: ${wt.total}</h4>
<h4>Wait Times</h4>
<table class="display wt-overall" cellpadding="0" cellspacing="0" border="0">
<thead><tr><th>Wait Time</th><th>Number</th><th>Percentage</th></tr></thead>
<tbody>
% for block in wt.get_blocks():
    <% bval = wt.get_wait_times(block).total %>
    <% bper = "%.2f%%" % (bval*100./wt.total) if wt.total else "-" %>
    <tr><td>${block}</td><td>${bval}</td><td>${bper}</td></tr>
% endfor
</tbody></table>
</div>

<br/><br/>
The number on the <b>Number</b> column is how many minutes a build waited to start, rounded down.<br/><br/>
</span>
</div>

<div class="wt-column">
<h4>Platform break down</h4>

% for platform in sorted(wt.get_platforms()):
    <% ptotal = wt.get_total(platform=platform) %>
    
    <div class="wt-container">
    <div class="wt-container-title">${platform}: ${ptotal}</div>
	<table class="display wt-platforms" cellpadding="0" cellspacing="0" border="0">
	<thead><tr><th>Wait Time</th><th>Number</th><th>Percentage</th></tr></thead>
	<tbody>
        % for block in wt.get_blocks(platform=platform):
            <% bval = wt.get_wait_times(block, platform=platform).total %>
            <% bper = "%.2f%%" % (bval*100./ptotal) if ptotal else "-" %>
            <tr class="gradeA"><td>${block}</td><td>${bval}</td><td>${bper}</td></tr>
        % endfor
    </tbody></table>
    </div>
% endfor
</div>

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

<b>Builds with no changes</b> (usually nightly builds): ${wt.no_changes}<br/><br/>
Rebuilds and forced rebuilds were excluded from the statistics.<br/><br/><br/>
% if wt.otherplatforms:
    <b>Other platforms</b> lister under <b>'other'</b> platforms: 
    <div id="wt-otherplatforms-less"><ul>
    % for b in list(wt.otherplatforms)[:5]:
        <li>${b}</li>
    % endfor
    </ul><a href="">more...</a></div>
    <div id="wt-otherplatforms-more" style="display:none"><ul>
    % for b in wt.otherplatforms:
        <li>${b}</li>
    % endfor
    </ul><a href="">less...</a></div><br/>
% endif
% if wt.unknownbuilders:
    <b>Unknown builders</b> (excluded from the stats):
    <div id="wt-unknownbuilders-less"><ul>
	% for b in list(wt.unknownbuilders)[:5]:
        <li>${b}</li>
    % endfor
	</ul><a href="">more...</a></div>
    <div id="wt-unknownbuilders-more" style="display:none"><ul>
	% for b in wt.unknownbuilders:
        <li>${b}</li>
    % endfor
	</ul><a href="">less...</a></div>
% endif

</div>
<div class="clear"></div>
<br/>Generated at ${h.pacific_time(None)}.

<script type="text/javascript">
$(document).ready(function() {
    $(".wt-overall, .wt-platforms").dataTable({
        "bFilter": false,
        "bSort": false,
        "bAutoWidth": false,
        "bPaginate": false,
        "bInfo": false,
      } );

    $("#starttime, #endtime").AnyTime_picker({ format: AnyTime_picker_format });
    $("#timeIntervalButton").click(updateWindowLocation);

    initAnyTimePickers();
    
    initToggleBoxes('#wt-unknownbuilders-more', '#wt-unknownbuilders-less');
    initToggleBoxes('#wt-otherplatforms-more', '#wt-otherplatforms-less');
});
</script>
</body>
</html>
