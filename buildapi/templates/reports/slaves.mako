<%inherit file="report.mako"/>
<%namespace file="util.mako" import="datepicker_menu"/>
<%! from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, BUILDERS_DETAIL_LEVELS %>

<%def name="title()">Slaves Report</%def>

<%def name="head()">
${h.tags.javascript_link(
    url('/dygraph-combined.js'),
)}
<script type="text/javascript" src="http://www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart']});

    var graphBusySilosChangeVisibility = null;

    $(document).ready(function() {
        google.setOnLoadCallback(initialize);

        function initialize() {
            var data_busy_url = updateUrlParams({format:'chart'});
            var query_busy = new google.visualization.Query(data_busy_url);
            query_busy.send(handleQueryResponse_IntBusy);
        }

        function handleQueryResponse_IntBusy(response) {
            if (response.isError()) {
                console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
                return;
            }

            var data = response.getDataTable();
            var g = new Dygraph.GVizChart(
                document.getElementById("slaves_int_busy_chart_div")
            ).draw(data, { 
                valueRange: [0, ${c.report.total_slaves()}],
                rollPeriod: 1,
                showRoller: true,
            });
        }

        function handleQueryResponse_IntBusySilos(response) {
            if (response.isError()) {
                console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
                return;
            }

            var data = response.getDataTable();
            graphBusySilos.draw(data, { 
                valueRange: [0, 120],
                rollPeriod: 100,
                showRoller: true,
                yAxisLabelFormatter: function(value) {
                    return value + '%';
                },
            });
        }

        var graphBusySilos = new Dygraph(
            document.getElementById("slaves_int_busy_silos_chart_div"),
            updateUrlParams({format:'chart', type:'silos'}),
            {
                valueRange: [0, 100],
                rollPeriod: 1,
                visibility: [ ${','.join(['true', 'true'] + ['false']*(len(c.report.silos) - 1))} ],
                showRoller: true,
                yAxisLabelFormatter: function(value) {
                    return value + '%';
                }
            }
        );

        graphBusySilosChangeVisibility = function (el) {
            graphBusySilos.setVisibility(parseInt(el.id), el.checked);
        }

        $(".srep-overall").dataTable({
             "bFilter": false,
             "bSort": false,
             "bAutoWidth": false,
             "bPaginate": false,
             "bInfo": false,
         });
        $("#slaves-results").dataTable({
            "bAutoWidth": true,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 25,
            "aoColumnDefs": [
                /* Average Build Duration % */ { "iDataSort": 5, "aTargets": [ 4 ] },
                /* Average Build Duration Seconds */ { "bSearchable": false, "bVisible": false, "aTargets": [ 5 ] },
                /* Success % */ { "iDataSort": 8, "aTargets": [ 7 ] },
                /* Success float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 8 ] },
                /* Warnings % */ { "iDataSort": 10, "aTargets": [ 9 ] },
                /* Warnings float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 10 ] },
                /* Failure % */ { "iDataSort": 12, "aTargets": [ 11 ] },
                /* Failure foat */ { "bSearchable": false, "bVisible": false, "aTargets": [ 12 ] },
            ],
            "aaSorting": [[11,'desc']],
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
</%def>

<div style="width:450px; float: left;">
<h2>Summary</h2>
<table class="display srep-overall" cellpadding="0" cellspacing="0" border="0">
  <thead><tr><th></th><th></th></tr></thead>
  <tbody>
  <%
      total = c.report.total_slaves()
      total_busy = c.report.endtime_total_busy()
      total_idle = c.report.endtime_total_idle()
  %>
    <tr><td>Total Slaves</td><td><b>${total}</b></td></tr>
    <tr><td>Starttime</td><td>${h.pacific_time(c.report.starttime)}</td></tr>
    <tr><td>Endtime</td><td>${h.pacific_time(c.report.endtime)}</td></tr>
    <tr>
        <td>Total interval monitored</td>
        <td>${h.strf_hms(c.report.endtime - c.report.starttime)}</td>
    </tr>
    <tr>
        <td>Slaves Busy at endtime</td>
        <td>${"%.2f" % (total_busy * 100. / total if total else 0)}%</td>
    </tr>
    <tr>
        <td>Slaves Idle at endtime</td>
        <td>${"%.2f" % (total_idle * 100. / total if total else 0)}%</td>
    </tr>
    <tr><td>Average Busy Time (%)</td><td>${"%.2f" % c.report.get_avg_busy()}%</td></tr>
    <tr>
        <td>last_int_size</td>
        <td>${c.report.last_int_size}s (${h.strf_hms(c.report.last_int_size)})</td>
    </tr>
    <tr>
        <td>int_size</td>
        <td>${c.report.int_size}s (${h.strf_hms(c.report.int_size)})</td>
    </tr>
  </tbody>
</table>
</div>

<div style="float:left; margin: 0px 20px">
  <h2>Number of Busy Slaves</h2>
  <div id="slaves_int_busy_chart_div" style="width: 700px; height: 280px"></div>
  <div id="slaves_int_busy_silos_chart_div" style="width: 700px; height: 280px; margin-top:20px"></div>
  <div style="width: 700px;"><b>Display: </b>
    <input type="checkbox" id="0" onClick="graphBusySilosChangeVisibility(this)" checked>
    <label for="0"> Totals</label>
    % for idx in xrange(len(c.report.silos)):
        <input type=checkbox id="${idx + 1}" onClick="graphBusySilosChangeVisibility(this)" 
            ${'checked' if idx < 1 else ''}>
        <label for="${idx + 1}"> ${c.report.silos[idx]}</label>
    % endfor
  </div>
</div>
<div style="margin: 20px">*Mouse over to highlight individual values. Click and drag to zoom. Double-click to zoom back out.</div>

<div class="clear"></div>

<%
def get_slave_details_url(slave_id):
    params = dict(request.params)
    params.update({'slave_id': slave_id, 'int_size': None})
    return url.current(action='slave_details', **params)
%>

<table class="display results" id="slaves-results" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Slave id</th>
    <th>Slave Name</th>
    <th>Busy Time %</th>
    <th>Last ${h.strf_hms(c.report.last_int_size)} Busy Time %</th>
    <th>Average Build Duration</th>
    <th>Average Build Duration Seconds</th>
    <th>Total Builds</th>
    <th>Success %</th>
    <th>Success</th>
    <th>Warnings %</th>
    <th>Warnings</th>
    <th>Failures All %</th>
    <th>Failures All</th>
    <th>Last ${h.strf_hms(c.report.last_int_size)} Failures All %</th>
    <th>Failure %</th>
    <th>Skipped %</th>
    <th>Exception %</th>
    <th>Retry %</th>
    <th>NO_RESULT (NULL) %</th>
    <th>Status at endtime</th>
  </tr>
</thead>
<tbody>
% for slave_id in c.report.slaves:
  <%
  slave = c.report.slaves[slave_id]
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
  srep_url = get_slave_details_url(slave.slave_id)
  %>
  <tr>
    <td>${slave.slave_id}</td>
    <td><a href="${srep_url}">${slave.name}</a></td>
    <td>${"%.2f" % slave.get_ptg_busy()}</td>
    <td>${"%.2f" % slave.get_last_int_ptg_busy()}</td>
    <td>${h.strf_hms(d_avg) if d_avg else '-'}</td>
    <td>${d_avg}</td>
    <td>${slave.total}</td>
    <td><span class="success">${"%.2f" % r_succ}</span></td>
    <td>${r_succ}</td>
    <td><span class="warnings">${"%.2f" % r_warn}</span></td>
    <td>${r_warn}</td>
    <td><span class="failure">${"%.2f" % r_all_fail}</span></td>
    <td>${"%.2f" % r_all_fail}</td>
    <td>${"%.2f" % slave.get_last_int_ptg_fail()}</td>
    <td>${"%.2f" % r_fail}</td>
    <td>${"%.2f" % r_skip}</td>
    <td>${"%.2f" % r_exc}</td>
    <td>${"%.2f" % r_ret}</td>
    <td>${"%.2f" % r_nores}</td>
    <td>${slave.endtime_status()}</td>
  </tr>
% endfor
</tbody></table>
<div class="clear"></div>
