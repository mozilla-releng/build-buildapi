<%inherit file="report.mako"/>
<%namespace file="util.mako" import="datepicker_menu, print_datetime_short"/>
<%! from buildapi.model.util import results_to_str %>
<%! from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, BUILDERS_DETAIL_LEVELS %>

<%def name="title()">Slave ${c.report.slave_id} Report</%def>
${h.tags.javascript_link(
    url('/dygraph-combined.js'),
)}

<%def name="head()">
<script type="text/javascript" src="http://www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart']});
    google.setOnLoadCallback(initialize);

    function initialize() {
        var data_url = updateUrlParams({format:'chart'});
        var query = new google.visualization.Query(data_url);
        query.send(handleQueryResponse_Failures);

        var data_busy_url = updateUrlParams({format:'chart', type:'busy'});
        var query_busy = new google.visualization.Query(data_busy_url);
        query_busy.send(handleQueryResponse_Busy);
    }

    function handleQueryResponse_Failures(response) {
        if (response.isError()) {
            console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
            return;
        }

        var data = response.getDataTable();
        var g = new Dygraph.GVizChart(
            document.getElementById("slave_fail_chart_div")
        ).draw(data, { 
            colors: ['green', 'orange', 'red'],
            yAxisLabelFormatter: function(value) {
                return value + '%';
            },
        });
    }

    function handleQueryResponse_Busy(response) {
        if (response.isError()) {
            console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
            return;
        }

        var data = response.getDataTable();
        var g = new Dygraph.GVizChart(
            document.getElementById("slave_busy_chart_div")
        ).draw(data, { 
            colors: ['green', 'orange', 'red'],
            fillGraph: true,
            strokeWidth: 0.5,
            valueRange: [0, 1.2],
            gridLineColor: '#FFF',
            yAxisLabelFormatter: function(value) {
                if (value == 0) return 'Idle';
                if (value == 1) return 'Busy';
                return '';
            },
        });
    }

    $(document).ready(function() {
        $(".srep-overall").dataTable({
             "bFilter": false,
             "bSort": false,
             "bAutoWidth": false,
             "bPaginate": false,
             "bInfo": false,
         });
         $(".srep-builds").dataTable({
             "bAutoWidth": true,
             "bProcessing": true,
             "bPaginate": true,
             "sPaginationType": "full_numbers",
             "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
             "iDisplayLength": 50,
             "aoColumnDefs": [
                 /* Result */ { "iDataSort": 3, "aTargets": [ 2 ] },
                 /* Result (number) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 3 ] },
                 /* Duration */ { "iDataSort": 5, "aTargets": [ 4 ] },
                 /* Duration (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 5 ] },
             ],
             "aaSorting": [[6,'desc']],
          });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
</%def>

<%
def get_builder_details_url(builder_name):
    params = dict(request.params)
    params.update(builder_name=builder_name)
    params.update(slave_id=None)
    return url.current(action='status_builder_details', **params)
%>

<div style="width:450px; float: left;">
<h2>Summary</h2>
<table class="display srep-overall" cellpadding="0" cellspacing="0" border="0">
  <thead><tr><th></th><th></th></tr></thead>
  <%
      slave = c.report
      # duration
      d_avg = slave.get_avg_duration()
      # results
      r = slave.get_ptg_results()
      r_succ = r[SUCCESS]
      r_warn = r[WARNINGS]
      r_fail = r[FAILURE]
      r_skip = r[SKIPPED]
      r_exc = r[EXCEPTION]
      r_ret = r[RETRY]
      r_nores = r[NO_RESULT]
      r_all_fail = r_fail + r_skip + r_exc + r_ret + r_nores
  %>
  <tbody>
    <tr><td>Slave Name</td><td><b>${slave.name}</b></td></tr>
    <tr><td>Slave id</td><td><b>${slave.slave_id}</b></td></tr>
    <tr><td>Starttime</td><td>${h.pacific_time(c.report.starttime)}</td></tr>
    <tr><td>Endtime</td><td>${h.pacific_time(c.report.endtime)}</td></tr>
    <tr><td>Total interval monitored</td><td>${h.strf_hms(c.report.endtime - c.report.starttime)}</td></tr>
    <tr><td>Busy Time (%)</td><td><b>${"%.2f" % slave.get_ptg_busy()}%</b></td></tr>
    <tr>
      <td>Last ${h.strf_hms(slave.last_int_size)} Busy Time (%)</td>
      <td>${"%.2f" % slave.get_last_int_ptg_busy()}%</td>
    </tr>
    <tr><td>Average Build Duration</td><td>${h.strf_hms(d_avg) if d_avg else '-'}</td></tr>
    <tr><td>Total Builds</td><td>${slave.total}</td></tr>
    <tr>
      <td>Results (%)</td>
      <td>
        <span class="success">S:${"%.2f" % r_succ}% </span>
        <span class="warnings">W:${"%.2f" % r_warn}% </span>
        <span class="failure">F:${"%.2f" % r_all_fail}% </span><br/>
        <span class="failure normal">Fail:${"%.2f" % r_fail}% </span><br/>
        <span class="failure normal">Skip:${"%.2f" % r_skip}% </span><br/>
        <span class="failure normal">Excep:${"%.2f" % r_exc}% </span><br/>
        <span class="failure normal">Retry:${"%.2f" % r_ret}% </span><br/>
        <span class="failure normal">NULL:${"%.2f" % r_nores}%</span>
    </td></tr>
    <tr>
      <td>Last ${h.strf_hms(c.report.last_int_size)} Failures (%)</td>
      <td><span class="failure">F:${"%.2f" % slave.get_last_int_ptg_fail()}%</span></td>
    </tr>
    <tr><td>last_int_size</td><td>${slave.last_int_size}s (${h.strf_hms(slave.last_int_size)})</td></tr>
    <tr><td>int_size</td><td>${slave.int_size}s (${h.strf_hms(slave.int_size)})</td></tr>
  </tbody>
</table>
</div>

<div style="float:left">
  <div id="slave_fail_chart_div" style="height: 300px"></div>
  <div id="slave_busy_chart_div" style="height: 200px"></div>
</div>
<div style="margin: 20px">*Mouse over to highlight individual values. Click and drag to zoom. Double-click to zoom back out.</div>

<div class="clear"></div>

<h2>Builds</h2>
<table class="display results srep-builds" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Builder id</th>
    <th>Builder name</th>
    <th>Result</th>
    <th>Result number</th>
    <th>Duration</th>
    <th>Duration seconds</th>
    <th>Starttime</th>
    <th>Endtime</th>
  </tr>
</thead>
<tbody>
<%!results_css_class = ['', 'success', 'warnings', 'failure']%>
% for build in c.report.builds:
  <%
  result = build.result if build.result != None else -1
  results_css = results_css_class[min(result, 2) + 1]
  brep_url = get_builder_details_url(build.builder_name)
  %>
  <tr class="${results_css}">
    <td>${build.builder_id}</td>
    <td><a href="${brep_url}">${build.builder_name}</a></td>
    <td><span class="${results_css}">${results_to_str(build.result)}</span></td>
    <td>${build.result}</td>
    <td>${h.strf_hms(build.duration) if build.duration else '-'}</td>
    <td>${build.duration}</td>
    <td>${print_datetime_short(build.starttime)}</td>
    <td>${print_datetime_short(build.endtime)}</td>
  </tr>
% endfor
</tbody></table>
</div>
<div class="clear"></div>
