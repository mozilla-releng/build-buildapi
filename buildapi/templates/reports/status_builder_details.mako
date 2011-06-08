<%inherit file="report.mako"/>
<%namespace file="util.mako" import="datepicker_menu"/>
<%! from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, BUILDERS_DETAIL_LEVELS %>

<%def name="title()">Status Builder Report ${c.report.name}</%def>

<%def name="head()">
${h.tags.javascript_link(
    url('/datatables.filters.js'),
)}
<script type="text/javascript" src="//www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart']});

    $(document).ready(function() {
        var srTable = $("#slaves-results").dataTable({
            "bAutoWidth": true,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 25,
            "aoColumnDefs": [
                /* Average Build Duration % */ { "iDataSort": 4, "aTargets": [ 3 ] },
                /* Average Build Duration Seconds */ { "bSearchable": false, "bVisible": false, "aTargets": [ 4 ] },
                /* Success % */ { "iDataSort": 6, "aTargets": [ 5 ] },
                /* Success float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 6 ] },
                /* Warnings % */ { "iDataSort": 8, "aTargets": [ 7 ] },
                /* Warnings float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 8 ] },
                /* Failure % */ { "iDataSort": 10, "aTargets": [ 9 ] },
                /* Failure foat */ { "bSearchable": false, "bVisible": false, "aTargets": [ 10 ] },
            ],
            "aaSorting": [[4,'desc']],
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
def get_slave_details_url(slave_id):
    params = dict(request.params)
    params.update(slave_id=slave_id)
    params.update(builder_name=None)
    return url.current(action='slave_details', **params)
%>

<table class="display results" id="slaves-results" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Slave id</th>
    <th>Slave Name</th>
    <th>Total Builds</th>
    <th>Average Build Duration</th>
    <th>Average Build Duration Seconds</th>
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
    <td>${slave.total}</td>
    <td>${h.strf_hms(d_avg) if d_avg else '-'}</td>
    <td>${d_avg}</td>
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
