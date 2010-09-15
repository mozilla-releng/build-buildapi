<%inherit file="report.mako"/>
<%namespace file="util.mako" import="branch_menu, datepicker_menu"/>
<%! from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY %>

<%def name="title()">Average Time per Builder Report</%def>

<%def name="head()">
<script type="text/javascript">
    $(document).ready(function() {
        var e2eTable = $("#builds-overall").dataTable({
            "bAutoWidth": false,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 50,
            "aoColumnDefs": [ 
                /* Avg Duration */ { "iDataSort": 7, "aTargets": [ 6 ] },
                /* Avg Duration (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 7 ] },
                /* Success % */ { "iDataSort": 10, "aTargets": [ 9 ] },
                /* Success float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 10 ] },
                /* Warnings % */ { "iDataSort": 12, "aTargets": [ 11 ] },
                /* Warnings float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 12 ] },
                /* Failure % */ { "iDataSort": 14, "aTargets": [ 13 ] },
                /* Failure foat */ { "bSearchable": false, "bVisible": false, "aTargets": [ 14 ] },
                /* Min Duration */ { "iDataSort": 16, "aTargets": [ 15 ] },
                /* Min Duration (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 16 ] },
                /* Max Duration */ { "iDataSort": 18, "aTargets": [ 17 ] },
                /* Max Duration (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 18 ] },
            ],
            "aaSorting": [[0,'asc'], [1,'asc'], [2,'asc'], [6,'desc']],
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${branch_menu(c.report.branch_name)}</p>
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
  <p>Running and pending build requests were excluded.</p>
</%def>

<%!import urllib %>
<%
def get_builder_details_url(buildername):
  params = dict(request.params)
  params['branch_name'] = None
  params['buildername'] = urllib.quote_plus(buildername)
  return url.current(action='builder_details', **params)
%>

<% r_sum = c.report.get_sum_duration() %>
<p>All sum duration: <b>${h.strf_hms(r_sum)}</b></p>

<p>Detail level:
  <input type="radio" name="detail_level" value="builder" checked /> builder
  <input type="radio" name="detail_level" value="job_type" /> job_type
  <input type="radio" name="detail_level" value="build_type" /> build_type
  <input type="radio" name="detail_level" value="platform" /> platform
</p>

<table class="display" id="builds-overall" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Platform</th>
    <th>Build Type</th>
    <th>Job Type</th>
    <th>Buildername</th>
    <th>SUM Duration</th>
    <th>PTG Duration %</th>
    <th>Avg Duration</th>
    <th>Avg Duration (seconds)</th>
    <th>No. breqs</th>
    <th>Success %</th>
    <th>Success float</th>
    <th>Warnings %</th>
    <th>Warnings float</th>
    <th>Failure %</th>
    <th>Failure foat</th>
    <th>Min Duration</th>
    <th>Min Duration (seconds)</th>
    <th>Max Duration</th>
    <th>Max Duration (seconds)</th>
  </tr>
</thead>
<tbody>
% for b in c.report.builders:
  <%
  brep = c.report.builders[b]
  # durations
  d_avg = brep.get_avg_duration()
  d_min = brep.get_min_duration()
  d_max = brep.get_max_duration()
  # results percentage
  r = brep.get_ptg_results()
  r_succ = r[SUCCESS]
  r_warn = r[WARNINGS]
  r_fail = r[FAILURE] + r[SKIPPED] + r[EXCEPTION] + r[RETRY]
  # builder datails url
  brep_url = get_builder_details_url(brep.buildername)
  %>
  <tr>
    <td>${brep.platform}</td>
    <td>${brep.build_type}</td>
    <td>${brep.job_type}</td>
    <td><a href="${brep_url}">${brep.buildername}</a></td>
    <td>${h.strf_hms(brep.get_sum_duration())}</td>
    <td>${"%.2f" % (brep.get_sum_duration()*100. / r_sum)}</td>
    <td><b>${h.strf_hms(d_avg) if d_avg else '-'}</b></td>
    <td>${d_avg}</td>
    <td>${brep.get_total_build_requests()}</td>
    <td><span class="success">${"%.2f" % r_succ}</span></td>
    <td>${r_succ}</td>
    <td><span class="warnings">${"%.2f" % r_warn}</span></td>
    <td>${r_warn}</td>
    <td><span class="failure">${"%.2f" % r_fail}</span></td>
    <td>${r_fail}</td>
    <td>${h.strf_hms(d_min)}</td>
    <td>${d_min}</td>
    <td>${h.strf_hms(d_max)}</td>
    <td>${d_max}</td>
  </tr>
% endfor
</tbody></table>
<div class="clear"></div>
