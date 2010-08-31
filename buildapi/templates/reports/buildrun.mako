<%inherit file="report.mako"/>
<%namespace file="util.mako" import="print_datetime_short, print_datetime"/>
<%! from buildapi.model.endtoend import BuildRequest, RESULTS_TO_STR %>

<%def name="title()">Build Run Report</%def>

<%def name="head()">
<script type="text/javascript">
    $(document).ready(function() {
        $(".brun-overall").dataTable({
            "bFilter": false,
            "bSort": false,
            "bAutoWidth": false,
            "bPaginate": false,
            "bInfo": false,
        });
        $(".brun-details").dataTable({
            "bAutoWidth": false,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 50,
            "aoColumnDefs": [ 
                /* results */ { "iDataSort": 2, "aTargets": [ 1 ] },
                /* results number */ { "bSearchable": false, "bVisible": false, "aTargets": [ 2 ] },
                /* duration */ { "iDataSort": 6, "aTargets": [ 5 ] },
                /* duration (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 6 ] },
                /* wait time */ { "iDataSort": 8, "aTargets": [ 7 ] },
                /* wait time (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 8 ] },
            ],
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>Build Run Report for revision <b>${c.report.revision}</b>.</p>
</%def>

<% brun = c.report %>

<h2>Summary</h2>
<table class="display brun-overall" cellpadding="0" cellspacing="0" border="0">
  <thead><tr><th></th><th></th></tr></thead>
  <tbody>
    <% span = brun.get_duration() %>
    <tr><td>Revision</td><td>${brun.revision}</td></tr>
    <tr><td>No. build requests</td><td>${brun.get_total_build_requests()}</td></tr>
    <tr><td>Unique no. build requests</td><td>${brun.get_unique_total_build_requests()}</td></tr>
    <tr><td>Duration</td><td>${h.strf_hms(span) if span else '-'}</td></tr>
    <tr><td>Least When Timestamp</td><td>${print_datetime(brun.lst_change_time)}</td></tr>
    <tr><td>Greatest Finish Time</td><td>${print_datetime(brun.gst_finish_time)}</td></tr>
    <tr><td>Complete</td><td>${brun.complete}</td></tr>
    <tr><td>Running</td><td>${brun.running}</td></tr>
    <tr><td>Pending</td><td>${brun.pending}</td></tr>
    <tr><td>Cancelled</td><td>${brun.cancelled}</td></tr>
    <tr><td>Interrupted</td><td>${brun.interrupted}</td></tr>
    <tr><td>Misc</td><td>${brun.misc}</td></tr>
    <tr><td>Rebuilds</td><td>${brun.rebuilds}</td></tr>
    <tr><td>Forcebuilds</td><td>${brun.forcebuilds}</td></tr>
    <tr>
      <td>Results</td>
      <td>
        <span class="success">S:${brun.results_success} </span>
        <span class="warnings">W:${brun.results_warnings} </span>
        <span class="failure">F:${brun.results_failure} </span>
        <span class="other">O:${brun.results_other} </span>
      </td></tr>
    <tr><td>Builds</td><td>${len(brun.builds)} (${len(set(brun.builds))}) ${','.join(map(str,set(brun.builds)))}</td></tr>
    <tr><td>Unittests</td><td>${len(brun.unittests)} (${len(set(brun.unittests))}) </td></tr>
    <tr><td>Talos</td><td>${len(brun.talos)} (${len(set(brun.talos))})</td></tr>
  </tbody>
</table>
<div class="clear"></div>

<h2>Build Requests</h2>
<table class="display brun-details results" cellpadding="0" cellspacing="0" border="0">
  <thead><tr>
    <th>status</th>
    <th>results</th>
    <th>results number</th>
    <th>buildername</th>
    <th>branch</th>
    <th>duration</th>
    <th>duration (seconds)</th>
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
    for br in brun.build_requests:
        table_row_brun_details(br)
    %>
  </tbody>
</table>
<div class="clear"></div>

<%!results_css_class = ['', 'success', 'warnings', 'failure']%>
<%def name="table_row_brun_details(br)">
<% 
duration = br.get_duration()
wait_time = br.get_wait_time()
results_css = results_css_class[min(br.results, 2) + 1]
%>
<tr class="${results_css}">
  <td>${BuildRequest.str_status(br.status)}</td>
  <td><span class="${results_css}">${RESULTS_TO_STR[br.results] if br.results in RESULTS_TO_STR else '-'}</span></td>
  <td>${br.results}</td>
  <td>${br.buildername}</td>
  <td>${br.branch}</td>
  <td>${h.strf_hms(duration) if duration else '-'}</td>
  <td>${duration}</td>
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
