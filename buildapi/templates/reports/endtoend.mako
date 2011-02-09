<%inherit file="report.mako"/>
<%namespace file="util.mako" import="print_datetime_short, branch_menu, datepicker_menu"/>
<%! from buildapi.model.util import status_to_str, results_to_str %>

<%def name="title()">End to End Times Report</%def>

<%def name="head()">
<script type="text/javascript">
    $(document).ready(function() {
        $("#changes-pending").dataTable({
            "bFilter": false,
            "bAutoWidth": false,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[5, 10, 20, -1], [5, 10, 20, "All"]],
            "iDisplayLength": 5,
            "aaSorting": [[4,'desc']],
        });
        var e2eTable = $("#e2e-overall").dataTable({
            "bAutoWidth": true,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 50,
            "aoColumnDefs": [ 
                /* Results */ { "iDataSort": 4, "aTargets": [ 3 ] },
                /* Results number */ { "bSearchable": false, "bVisible": false, "aTargets": [ 4 ] },
                /* Duration */ { "iDataSort": 8, "aTargets": [ 7 ] },
                /* Duration (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 8 ] },
            ],
            "aaSorting": [[9,'desc']],
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${branch_menu(c.report.branch_name)}</p>
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
</%def>

<div style="float:left; padding: 0px 20px 20px 20px;">
  <h2>Summary</h2>
  Branch name: <b>${c.report.branch_name}</b><br />
  Total build requests: <b>${c.report.get_total_build_requests()}</b><br />
  Unique total build requests: <b>${c.report.get_unique_total_build_requests()}</b><br />
  Build runs: <b>${c.report.get_total_build_runs()}</b><br />
  Average build run duration: <b>${h.strf_hms(c.report.get_avg_duration())}</b>
</div>

<div style="width:55%; float:right;">
<b>Pending changes</b>
<table class="display" id="changes-pending" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>changeid</th>
    <th>revision</th>
    <th>build run (tentative)</th>
    <th>branch</th>
    <th>when_timestamp</th>
  </tr>
</thead>
<tbody>
  % for cid in c.report.pending_changes:
    <% change = c.report.pending_changes[cid] %>
    <tr>
        <td>${change.changeid}</td>
        <td>${change.revision}</td>
        <td>${change.ss_revision}</td>
        <td>${change.branch}</td>
        <td>${print_datetime_short(change.when_timestamp)}</td>
    </tr>
  % endfor
</tbody>
</table>
</div>
<div class="clear"></div>

<table class="display results" id="e2e-overall" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Revision</th>
    <th>Changes Revisions</th>
    <th>Authors</th>
    <th>Results</th>
    <th>Results number</th>
    <th>Complete</th>
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
    <th>Pending Changes</th>
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
    <td>${' '.join([rev if rev else 'None' for rev in brun.changes_revision])}</td>
    <td>${' '.join([auth for auth in brun.authors if auth not in (None, 'sendchange-unittest', 'sendchange')])}</td>
    <td><span class="${results_css}">${results_to_str(brun.results)}</span></td>
    <td>${brun.results}</td>
    <td>${'yes' if brun.is_complete() else 'no'}</td>
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
    <td>${brun.builds}</td>
    <td>${brun.unittests}</td>
    <td>${brun.talos}</td>
    <td>${', '.join(map(str, sorted(brun.pending_changes, key=lambda x: x.changeid)))}</td>
  </tr>
% endfor
</tbody></table>
<div class="clear"></div>
