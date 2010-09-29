<%inherit file="report.mako"/>
<%namespace file="util.mako" import="branch_menu, datepicker_menu, builders_table_filters_menu"/>
<%! from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, BUILDERS_DETAIL_LEVELS %>

<%def name="title()">Average Time per Builder Report</%def>

<%def name="head()">
${h.tags.javascript_link(
    url('/DataTables-1.7.1/extras/fnGetNodes.js'),
    url('/datatables.filters.js'),
)}
<script type="text/javascript" src="http://www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart']});

    $(document).ready(function() {
        var e2eTable = $("#builders-overall").dataTable({
            "bAutoWidth": false,
            "bProcessing": true,
            "bPaginate": true,
            "sPaginationType": "full_numbers",
            "aLengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
            "iDisplayLength": 50,
            "aoColumnDefs": [
                /* Level */ { "bSearchable": false, "bVisible": false, "aTargets": [ 0 ] },
                /* SUM Run Time */ { "iDataSort": 6, "aTargets": [ 5 ]},
                /* SUM Run Time seconds */ { "bSearchable": false, "bVisible": false, "aTargets": [ 6 ] },
                /* Avg Run Time */ { "iDataSort": 9, "aTargets": [ 8 ] },
                /* Avg Run Time (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 9 ] },
                /* Success % */ { "iDataSort": 12, "aTargets": [ 11 ] },
                /* Success float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 12 ] },
                /* Warnings % */ { "iDataSort": 14, "aTargets": [ 13 ] },
                /* Warnings float */ { "bSearchable": false, "bVisible": false, "aTargets": [ 14 ] },
                /* Failure % */ { "iDataSort": 16, "aTargets": [ 15 ] },
                /* Failure foat */ { "bSearchable": false, "bVisible": false, "aTargets": [ 16 ] },
                /* Min Run Time */ { "iDataSort": 18, "aTargets": [ 17 ] },
                /* Min Run Time (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 18 ] },
                /* Max Run Time */ { "iDataSort": 20, "aTargets": [ 19 ] },
                /* Max Run Time (seconds) */ { "bSearchable": false, "bVisible": false, "aTargets": [ 20 ] },
                /* Buildername raw string */ { "bSearchable": false, "bVisible": false, "aTargets": [ 21 ] },
            ],
            "aaSorting": [[1,'asc'], [2,'asc'], [3,'asc'], [7,'desc']],
            "bla": "wooo",
        });

        var filterNameList = ['detail_level', 'platform', 'build_type', 'job_type'];        
        var filters = parseFiltersFromUrl(filterNameList);

        var oTableFilterWrapper = e2eTable.fnCreateFilterWrapper({
            tableFilterCols: {platform: 1, build_type: 2, job_type: 3, detail_level: 0},
            platformCol: 1,
            buildTypeCol: 2,
            jobTypeCol: 3,
            buildernameCol: 21,
            ptgRunTimeCol: 7,
            sumRunTimeCol: 6,
        });
        oTableFilterWrapper.applyFilters(filters);

        var oFilters = $("#builders-overall-filters").filters(filters, {
            onChangeCallback: function(filterName, checkedList) {
                oTableFilterWrapper.applyFilter(filterName, checkedList);
                oTableFilterWrapper.updatePtgColumn();
                // update pie chart
                var chartData = oTableFilterWrapper.parsePtgRunTimeChartData();
                updatePieChart(document.getElementById('piechart'), chartData);
            }
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
    buildername = buildername or ''
    params = dict(request.params)
    params.update(buildername = urllib.quote_plus(buildername), branch_name = None, revision = None)
    return url.current(action='builder_details', **params)
%>

<% r_sum = c.report.get_sum_run_time() %>
<p>All sum run_time: <b>${h.strf_hms(r_sum)}</b></p><p/>

<div id="piechart" style="float: right; margin-top: -120px; margin-bottom: -40px;"></div>

${builders_table_filters_menu('builders-overall-filters')}
<table class="display" id="builders-overall" cellpadding="0" cellspacing="0" border="0">
<thead>
  <tr>
    <th>Level</th>
    <th>Platform</th>
    <th>Build Type</th>
    <th>Job Type</th>
    <th>Buildername</th>
    <th>SUM Run Time</th>
    <th>SUM Run Time seconds</th>
    <th>PTG Run Time %</th>
    <th>Avg Run Time</th>
    <th>Avg Run Time (seconds)</th>
    <th>No. breqs</th>
    <th>Success %</th>
    <th>Success float</th>
    <th>Warnings %</th>
    <th>Warnings float</th>
    <th>Failure %</th>
    <th>Failure foat</th>
    <th>Min Run Time</th>
    <th>Min Run Time (seconds)</th>
    <th>Max Run Time</th>
    <th>Max Run Time (seconds)</th>
    <th>Buildername raw string</th>
  </tr>
</thead>
<tbody>
  % for brep in c.report.get_builders(leafs_only=False):
    ${table_row_brep_details(brep)}
  % endfor
</tbody>
</table>
<div class="clear"></div>

<%def name="table_row_brep_details(brep)">
<%
  # run_times
  d_avg = brep.get_avg_run_time()
  d_min = brep.get_min_run_time()
  d_max = brep.get_max_run_time()
  # results percentage
  r = brep.get_ptg_results()
  r_succ = r[SUCCESS]
  r_warn = r[WARNINGS]
  r_fail = r[FAILURE] + r[SKIPPED] + r[EXCEPTION] + r[RETRY]
  # builder datails url
  brep_url = get_builder_details_url(brep.buildername)
%>
  <tr>
    <td>${BUILDERS_DETAIL_LEVELS[brep.detail_level]}</td>
    <td>${brep.platform}</td>
    <td>${brep.build_type}</td>
    <td>${brep.job_type}</td>
    <td><a href="${brep_url}">${brep.buildername}</a></td>
    <td>${h.strf_hms(brep.get_sum_run_time())}</td>
    <td>${brep.get_sum_run_time()}</td>
    <td>${"%.2f" % (brep.get_sum_run_time()*100. / r_sum if r_sum else 0)}</td>
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
    <td>${brep.buildername}</td>
  </tr>
</%def>
