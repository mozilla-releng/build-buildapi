<%inherit file="report.mako"/>
<%namespace file="util.mako" import="datepicker_menu, int_size_menu"/>

<%def name="title()">Pushes Report</%def>

<%def name="head()">
<script type="text/javascript" src="//www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart', 'table']});
    google.setOnLoadCallback(initialize);

    function initialize() {
        var data_url_int = updateUrlParams({format:'chart', type: 'int'});
        var query_int = new google.visualization.Query(data_url_int);
        query_int.send(handleQueryResponseIntervals);

        var data_url_all = updateUrlParams({format:'chart', type: 'all'});
        var query_all = new google.visualization.Query(data_url_all);
        query_all.send(handleQueryResponseAll);

        var data_url_hourly = updateUrlParams({format:'chart', type: 'hourly'});
        var query_hourly = new google.visualization.Query(data_url_hourly);
        query_hourly.send(handleQueryResponseHourly);
    }

    function handleQueryResponseIntervals(response) {
        if (response.isError()) {
           console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
           return;
        }

        var data = response.getDataTable();
        var data_no_totals = jQuery.extend(true, {}, data);
        data_no_totals.removeColumn(1);

        drawLineChart(document.getElementById('line_chart_div'), data, false,
            'Pushes', 1400, 300, 8);
        drawColumnChart(document.getElementById('column_chart_div'), data_no_totals, true,
            'Pushes', 1400, 300, 8);
    }

    function handleQueryResponseAll(response) {
        if (response.isError()) {
           console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
           return;
        }

        var data = response.getDataTable();
        drawPieChart(document.getElementById('pie_chart_div'), data, 
            'Number of Pushes by Branch', 1100, 600);
    }

    function handleQueryResponseHourly(response) {
        if (response.isError()) {
           console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
           return;
        }

        var data = response.getDataTable();
        drawColumnChart(document.getElementById('hourly_column_chart_div'), data, 
            'Average Number of Pushes by Hour', 1400, 300, 8);
    }

    $(document).ready(function() {
        $(".pushes-overall").dataTable({
            "bFilter": false,
            "bAutoWidth": false,
            "bPaginate": false,
            "bInfo": false,
        } );
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and <b>${h.pacific_time(c.report.endtime)}</b></p>
  <p>
    <b>int_size</b> = ${c.report.int_size}s (${h.strf_hms(c.report.int_size)}) | 
    ${int_size_menu()}
  </p>
</%def>

<div>
  <table class="display pushes-overall" cellpadding="0" cellspacing="0" border="0">
    <thead>
      <tr>
        <th>Branch</th>
        <th>Totals</th>
        % for int_idx in range(c.report.int_no):
          <th>${h.pacific_time(c.report.get_interval_timestamp(int_idx), format='%m/%d %H:%M:%S')}</th>
        % endfor
      </tr></thead>
    <tbody>
      <tr class="gradeA">
        <td>&nbsp;Totals</td><td>${c.report.total}</td>
          % for val in c.report.get_intervals():
            <td>${val}</td>
          % endfor
      </tr>
      % for branch in sorted(c.report.branches):
        <tr>
          <td>${branch}</td>
          <td style="background-color:#EEFFEE">${c.report.get_total(branch=branch)}</td>
          % for val in c.report.get_intervals(branch=branch):
            <td>${val}</td>
          % endfor
        </tr>
      % endfor
    </tbody>
  </table>
</div>
<div class="clear"></div>

<div id="table_div"></div>
<div id="line_chart_div"></div>
<div id="column_chart_div"></div>
<div id="hourly_column_chart_div"></div>
<div id="pie_chart_div"></div>
