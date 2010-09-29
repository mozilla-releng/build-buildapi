<%inherit file="report.mako"/>
<%namespace file="util.mako" import="datepicker_menu, print_datetime_short, print_datetime"/>
<%! from buildapi.model.util import status_to_str, results_to_str, NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY %>

<%def name="title()">Builder Report: ${c.report.buildername}</%def>

<%def name="head()">
<script type="text/javascript">
    $(document).ready(function() {
        $(".brep-overall").dataTable({
            "bFilter": false,
            "bSort": false,
            "bAutoWidth": false,
            "bPaginate": false,
            "bInfo": false,
        });
        $(".brep-details").dataTable({
            "bAutoWidth": false,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 50,
            "aoColumnDefs": [
                /* results */ { "iDataSort": 3, "aTargets": [ 2 ] },
                /* results number */ { "bSearchable": false, "bVisible": false, "aTargets": [ 3 ] },
                /* run_time */ { "iDataSort": 7, "aTargets": [ 6 ] },
                /* run_time (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 7 ] },
                /* wait time */ { "iDataSort": 9, "aTargets": [ 8 ] },
                /* wait time (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 9 ] },
            ],
            "aaSorting": [[10,'desc']],
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
  <p>Running and pending build requests were excluded.</p>
</%def>

<% brep = c.report %>

<h2>Summary</h2>
<table class="display brep-overall" cellpadding="0" cellspacing="0" border="0">
  <thead><tr><th></th><th></th></tr></thead>
  <tbody>
    <tr><td>Buildername</td><td>${brep.buildername}</td></tr>
    <tr><td>Platform</td><td>${brep.platform}</td></tr>
    <tr><td>Build Type</td><td>${brep.build_type}</td></tr>
    <tr><td>Job Type</td><td>${brep.job_type}</td></tr>
    <tr><td>No. build requests</td><td>${brep.get_total_build_requests()}</td></tr>
    <tr><td>Results</td><td>${print_results_ptg_full(brep.get_ptg_results())}</td></tr>
    <tr><td>Min Run Time</td><td>${h.strf_hms(brep.get_min_run_time())}</td></tr>
    <tr><td>Max Run Time</td><td>${h.strf_hms(brep.get_max_run_time())}</td></tr>
    <tr><td><b>Avg Run Time</b></td><td><b>${h.strf_hms(brep.get_avg_run_time())}</b></td></tr>
  </tbody>
</table>
<div class="clear"></div>

<h2>Build Requests</h2>
<table class="display brep-details results" cellpadding="0" cellspacing="0" border="0">
  <thead><tr>
    <th>revision</th>
    <th>status</th>
    <th>results</th>
    <th>results number</th>
    <th>buildername</th>
    <th>branch</th>
    <th>run_time</th>
    <th>run_time (seconds)</th>
    <th>wait time</th>
    <th>wait time (seconds)</th>
    <th>when_timestamp</th>
    <th>submitted_at</th>
    <th>claimed_at</th>
    <th>start_time</th>
    <th>complete_at</th>
    <th>finish_time</th>
    <th>complete</th>
    <th>reason</th>
    <th>number</th>
    <th>brid</th>
    <th>buildsetid</th>
    <th>ssid</th>
    <th>author</th>
    <th>comments</th>
    <th>revlink</th>
    <th>category</th>
    <th>repository</th>
    <th>project</th>
  </tr></thead>
  <tbody>
    <%
    for br in brep.build_requests:
        table_row_brep_details(br)
    %>
  </tbody>
</table>
<div class="clear"></div>

<%!results_css_class = ['', 'success', 'warnings', 'failure']%>
<%def name="table_row_brep_details(br)">
<%
run_time = br.get_run_time()
wait_time = br.get_wait_time()
br_url = url.current(action='endtoend_revision', revision=br.revision, branch_name=br.branch_name, buildername=None)
results_css = results_css_class[min(br.results, 2) + 1]
%>
<tr class="${results_css}">
  <td><a href="${br_url}">${br.revision}</a></td>
  <td>${status_to_str(br.status)}</td>
  <td><span class="${results_css}">${results_to_str(br.results)}</span></td>
  <td>${br.results}</td>
  <td>${br.buildername}</td>
  <td>${br.branch}</td>
  <td>${h.strf_hms(run_time) if run_time else '-'}</td>
  <td>${run_time}</td>
  <td>${h.strf_hms(wait_time) if wait_time else '-'}</td>
  <td>${wait_time}</td>
  <td>${print_datetime_short(br.when_timestamp)}</td>
  <td>${print_datetime_short(br.submitted_at)}</td>
  <td>${print_datetime_short(br.claimed_at)}</td>
  <td>${print_datetime_short(br.start_time)}</td>
  <td>${print_datetime_short(br.complete_at)}</td>
  <td>${print_datetime_short(br.finish_time)}</td>
  <td>${br.complete}</td>
  <td>${br.reason}</td>
  <td>${br.number}</td>
  <td>${br.brid}</td>
  <td>${br.buildsetid}</td>
  <td>${br.ssid}</td>
  <td>${br.author}</td>
  <td>${br.comments}</td>
  <td>${br.revlink}</td>
  <td>${br.category}</td>
  <td>${br.repository}</td>
  <td>${br.project}</td>
</tr>
</%def>

<%def name="print_results_ptg_full(r)">
  <span class="success">S:${"%.2f" % r[SUCCESS]}% </span>
  <span class="warnings">W:${"%.2f" % r[WARNINGS]}% </span>
  <span class="failure">F:${"%.2f" % r[FAILURE]}% </span>
  <span class="failure">S:${"%.2f" % r[SKIPPED]}% </span>
  <span class="failure">E:${"%.2f" % r[EXCEPTION]}% </span>
  <span class="failure">R:${"%.2f" % r[RETRY]}% </span>
  <span class="other">O:${"%.2f" % r[NO_RESULT]}% </span>
</%def>
