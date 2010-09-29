<%inherit file="report.mako"/>
<%namespace file="util.mako" import="print_datetime_short, branch_menu, datepicker_menu"/>
<%! from buildapi.model.util import status_to_str, results_to_str %>

<%def name="title()">Try Chooser Report</%def>

<%def name="head()">
<script type="text/javascript" src="http://www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart']});
    google.setOnLoadCallback(initialize);

    function initialize() {
        ${c.jscode_data_authors}
        ${c.jscode_data_runs}

        drawPieChart(document.getElementById('chart_authors_div'), jscode_data_authors, 'Authors Used TryChooser');
        drawPieChart(document.getElementById('chart_runs_div'), jscode_data_runs, 'BuildRuns Used TryChooser');
    }

    $(document).ready(function() {
        var e2eTable = $("#e2e-overall").dataTable({
            "bAutoWidth": false,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 50,
            "aoColumnDefs": [ 
                /* Results */ { "iDataSort": 2, "aTargets": [ 1 ] },
                /* Results number */ { "bSearchable": false, "bVisible": false, "aTargets": [ 2 ] },
                /* Duration */ { "iDataSort": 8, "aTargets": [ 7 ] },
                /* Duration (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 8 ] },
            ],
            "aaSorting": [[7,'desc']],
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${branch_menu(c.report.branch_name)}</p>
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
</%def>

<div id="chart_authors_div" style="margin: 0px -20px -20px; float: right;"></div>
<div id="chart_runs_div" style="margin: 0px -20px -20px; float: right;"></div>

<div>Branch name: <b>${c.report.branch_name}</b></div>
<div>Total build requests: <b>${c.report.get_total_build_requests()}</b></div>
<div>Unique total build requests: <b>${c.report.get_unique_total_build_requests()}</b></div>
<div>Build runs: <b>${c.report.get_total_build_runs()}</b></div>
<div>Average build run duration: <b>${h.strf_hms(c.report.get_avg_duration())}</b></div>
<br/>
<div><b>Used TryChooser (${len(c.report.get_used_trychooser())}):</b> ${', '.join(sorted(c.report.get_used_trychooser()))}</div>
<div><b>Not Used TryChooser (${len(c.report.get_not_used_trychooser())}):</b> ${', '.join(sorted(c.report.get_not_used_trychooser()))}</div>
<div><b>Never Used TryChooser (${len(c.report.get_never_used_trychooser())}):</b> ${', '.join(sorted(c.report.get_never_used_trychooser()))}</div>
<% used_and_not_used = c.report.get_used_trychooser() &  c.report.get_not_used_trychooser()%>
<div><b>Both used and Not Used TryChooser (${len(used_and_not_used)}):</b> ${', '.join(sorted(used_and_not_used))}</div>
<br/>

<table class="display results" id="e2e-overall" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Revision</th>
    <th>Results</th>
    <th>Results number</th>
    <th>Complete</th>
    <th>Uses TryChooser</th>
    <th>Uses TryChooser Comments</th>
    <th>No. build requests</th>
    <th>Duration</th>
    <th>Duration (seconds)</th>
    <th>Least When Timestamp</th>
    <th>Greatest Finish Time</th>
    <th>Complete</th>
    <th>Running</th>
    <th>Pending</th>
    <th>Cancelled</th>
    <th>Interrupted</th>
    <th>Misc</th>
    <th>Rebuilds</th>
    <th>Forcebuilds</th>
    <th>Builds</th>
    <th>Unittests</th>
    <th>Talos</th>
  </tr>
</thead>
<tbody>

<%!results_css_class = ['', 'success', 'warnings', 'failure']%>
% for brun_key in c.report._runs:
  <%
  brun = c.report._runs[brun_key] 
  duration = brun.get_duration()
  brun_url = url.current(action='endtoend_revision', revision=brun.revision, branch_name=brun.branch_name)
  results_css = results_css_class[min(brun.results, 2) + 1]
  %>
  <tr class="${results_css}">
    <td><a href="${brun_url}">${brun.revision}</a></td>
    <td><span class="${results_css}">${results_to_str(brun.results)}</span></td>
    <td>${brun.results}</td>
    <td>${'yes' if brun.is_complete() else 'no'}</td>
    <td>${all(brun.uses_try_chooser.values())}</td>
    <td>${' '.join(['%s:%s' % (k, v) for k, v in brun.uses_try_chooser.items()])}</td>
    <td>${brun.get_total_build_requests()}</td>
    <td>${h.strf_hms(duration) if duration else '-'}</td>
    <td>${duration}</td>
    <td>${print_datetime_short(brun.lst_change_time)}</td>
    <td>${print_datetime_short(brun.gst_finish_time)}</td>
    <td>${brun.complete}</td>
    <td>${brun.running}</td>
    <td>${brun.pending}</td>
    <td>${brun.cancelled}</td>
    <td>${brun.interrupted}</td>
    <td>${brun.misc}</td>
    <td>${brun.rebuilds}</td>
    <td>${brun.forcebuilds}</td>
    <td>${len(brun.builds)} (${len(set(brun.builds))})</td>
    <td>${len(brun.unittests)} (${len(set(brun.unittests))})</td>
    <td>${len(brun.talos)} (${len(set(brun.talos))})</td>
  </tr>
% endfor
</tbody></table>
<div class="clear"></div>
