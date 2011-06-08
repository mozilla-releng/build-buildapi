<%inherit file="report.mako"/>
<%namespace file="util.mako" import="datepicker_menu"/>
<%! from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, BUILDERS_DETAIL_LEVELS %>

<%def name="title()">Status Builders Report</%def>

<%def name="head()">
${h.tags.javascript_link(
    url('/datatables.filters.js'),
)}
<script type="text/javascript" src="//www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart']});

    $(document).ready(function() {
        var srTable = $("#builders-results").dataTable({
            "bAutoWidth": true,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 25,
            "aoColumnDefs": [
                /* Average Build Duration % */ { "iDataSort": 3, "aTargets": [ 2 ] },
                /* Average Build Duration Seconds */ { "bSearchable": false, "bVisible": false, "aTargets": [ 3 ] },
                /* Success % */ { "iDataSort": 6, "aTargets": [ 5 ] },
                /* Success float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 6 ] },
                /* Warnings % */ { "iDataSort": 8, "aTargets": [ 7 ] },
                /* Warnings float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 8 ] },
                /* Failure % */ { "iDataSort": 10, "aTargets": [ 9 ] },
                /* Failure foat */ { "bSearchable": false, "bVisible": false, "aTargets": [ 10 ] },
            ],
            "aaSorting": [[0,'asc']],
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
  <p><b>Total interval monitored: ${h.strf_hms(c.report.endtime - c.report.starttime)}</b></p>
</%def>

<%
def get_builder_details_url(builder_name):
    params = dict(request.params)
    params.update(builder_name=builder_name)
    return url.current(action='status_builder_details', **params)
%>

<table class="display results" id="builders-results" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Builder Name</th>
    <th>Total Builds</th>
    <th>Average Build Duration</th>
    <th>Average Build Duration Seconds</th>
    <th>Slaves</th>
    <th>Success %</th>
    <th>Success</th>
    <th>Warnings %</th>
    <th>Warnings</th>
    <th>Failures All %</th>
    <th>Failures All</th>
    <th>Failure %</th>
    <th>Skipped %</th>
    <th>Exception %</th>
    <th>Retry %</th>
    <th>NO_RESULT (NULL) %</th>
  </tr>
</thead>
<tbody>
% for builder_name in c.report.builders:
  <%
  builder = c.report.builders[builder_name]
  # duration
  d_avg = builder.get_avg_duration()
  # results
  r = builder.get_ptg_results()
  r_succ = r[SUCCESS]
  r_warn = r[WARNINGS]
  r_fail = r[FAILURE]
  r_skip = r[SKIPPED]
  r_exc = r[EXCEPTION]
  r_ret = r[RETRY]
  r_nores = r[NO_RESULT]
  r_all_fail = r_fail + r_skip + r_exc + r_ret + r_nores
  brep_url = get_builder_details_url(builder.name)
  %>
  <tr>
    <td><a href="${brep_url}">${builder.name}</a></td>
    <td>${builder.total}</td>
    <td>${h.strf_hms(d_avg) if d_avg else '-'}</td>
    <td>${d_avg}</td>
    <td>${len([builder.slaves[s].name for s in builder.slaves])}</td>
    <td><span class="success">${"%.2f" % r_succ}</span></td>
    <td>${r_succ}</td>
    <td><span class="warnings">${"%.2f" % r_warn}</span></td>
    <td>${r_warn}</td>
    <td><span class="failure">${"%.2f" % r_all_fail}</span></td>
    <td>${"%.2f" % r_all_fail}</td>
    <td>${"%.2f" % r_fail}</td>
    <td>${"%.2f" % r_skip}</td>
    <td>${"%.2f" % r_exc}</td>
    <td>${"%.2f" % r_ret}</td>
    <td>${"%.2f" % r_nores}</td>
  </tr>
% endfor
</tbody></table>
<div class="clear"></div>
