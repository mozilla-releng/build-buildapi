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
    )}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/dataTables-1.6/media/css/demo_page.css')}";
@import "${url('/dataTables-1.6/media/css/demo_table_jui.css')}";
@import "${url('/anytime/anytime.css')}";
@import "${url('/build-status.css')}";
</style>
</head>
<%
  import time
  wt = c.wait_times
  minutes_per_block = wt['minutes_per_block']
%>
<body id="dt_example">
<h1>Wait Times</h1>
<div>
<p>Build pool: 
% if wt['pool'] == 'buildpool':
    <b>buildpool</b> |
% else:
    <a href="${url.current(pool='buildpool', **dict(request.params))}">buildpool</a> |
% endif
% if wt['pool'] == 'trybuildpool':
    <b>trybuildpool</b>
% else:
    <a href="${url.current(pool='trybuildpool', **dict(request.params))}">trybuildpool</a>
% endif
</p><p>
<label for="starttime">Jobs submitted between</label>
<input type="text" id="starttime" size="26" value="" ref="${wt['starttime']}"/>
<label for="endtime2">and</label>
<input type="text" id="endtime" size="26" value="" ref="${wt['endtime']}"/>
<input type="button" id="timeIntervalButton" value="Go!"/>
</p><br/>
</div>
<div>
<div>Wait time report for <b>${wt['pool']}</b> for jobs submitted between <b>${h.pacific_time(wt['starttime'])}</b> 
and <b>${h.pacific_time(wt['endtime'])}</b></div>

<div id="wt-stats">
<div class="wt-column-s">

<div class="wt-container">
<h4>Total Jobs: ${wt['total']}</h4>
<h4>Wait Times</h4>
<table class="display wt-overall" cellpadding="0" cellspacing="0" border="0">
<thead><tr><th>Wait Time</th><th>Number</th><th>Percentage</th></tr></thead>
<tbody>
% for block in range(0, max(wt['wt'].keys())+1, minutes_per_block):
    <% bval = wt['wt'].get(block, {'total': 0, 'interval':[]})['total'] %>
    <% bper = "%.2f%%" % (bval*100./wt['total']) if wt['total'] else "-" %>
    <tr><td>${block}</td><td>${bval}</td><td>${bper}</td></tr>
% endfor
</tbody></table>
</div>

<br/><br/>
The number on the <b>Number</b> column is how many minutes a build waited to start, rounded down.<br/><br/>
<b>Builds with no changes</b> (usually nightly builds): ${wt['no_changes']}<br/><br/>
Rebuilds and forced rebuilds were excluded from the statistics.<br/><br/><br/>
% if wt['otherplatforms']:
    <b>Other platforms</b> lister under <b>'other'</b> platforms: ${', '.join(wt['otherplatforms'])}.<br/><br/>
% endif
% if wt['unknownbuilders']:
    <b>Unknown builders</b> (excluded from the stats): ${', '.join(wt['unknownbuilders'])}.<br/><br/>
% endif
</span>
</div>

<div class="wt-column">
<h4>Platform break down</h4>

% for platform in sorted(wt['platforms']):
    <% ptotal = wt['platforms'][platform]['total'] %>
    <% pwt = wt['platforms'][platform]['wt'] %>
    
    <div class="wt-container">
    <div class="wt-container-title">${platform}: ${ptotal}</div>
	<table class="display wt-platforms" cellpadding="0" cellspacing="0" border="0">
	<thead><tr><th>Wait Time</th><th>Number</th><th>Percentage</th></tr></thead>
	<tbody>
        % for block in range(0, max(pwt.keys())+1, minutes_per_block):
            <% bval = pwt.get(block, {'total': 0, 'interval':[]})['total'] %>
            <% bper = "%.2f%%" % (bval*100./ptotal) if ptotal else "-" %>
            <tr class="gradeA"><td>${block}</td><td>${bval}</td><td>${bper}</td></tr>
        % endfor
    </tbody></table>
    </div>
% endfor
</div>

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
});
</script>
</body>
</html>
