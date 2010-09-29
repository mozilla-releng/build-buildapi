<%inherit file="report.mako"/>
<%namespace file="util.mako" import="build_pool_menu, datepicker_menu, more_less_item_list"/>

<%def name="title()">Wait times Report</%def>

<%def name="head()">
<script type="text/javascript" src="http://www.google.com/jsapi"></script>
<script type="text/javascript">
    google.load('visualization', '1', {'packages':['corechart']});
    google.setOnLoadCallback(initialize);

    function initialize() {
        var data_url = updateUrlParams({format:'chart', num: 'ptg'});
        var query = new google.visualization.Query(data_url);
        query.send(handleQueryResponse_WaitTimesPercentage);

        ${c.jscode_data}
        drawColumnChart(document.getElementById('stacked_column_chart_full_div'), jscode_data, true,
            'Wait Times - Column Chart Job Numbers Stacked');
        drawColumnChart(document.getElementById('column_chart_full_div'), jscode_data, false,
            'Wait Times - Column Chart Job Numbers');
        drawAreaChart(document.getElementById('stacked_area_chart_full_div'), jscode_data, true,
            'Wait Times - Area Chart Job Numbers Stacked');
        drawAreaChart(document.getElementById('area_chart_full_div'), jscode_data, false,
            'Wait Times - Area Chart Job Numbers');
        drawLineChart(document.getElementById('line_chart_full_div'), jscode_data, false,
            'Wait Times - Line Chart Job Numbers');
    }

    function handleQueryResponse_WaitTimesFull(response) {
        if (response.isError()) {
            console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
            return;
        }

        var data = response.getDataTable();
        drawColumnChart(document.getElementById('column_chart_div'), data, true);
    }

    function handleQueryResponse_WaitTimesPercentage(response) {
        if (response.isError()) {
            console.error('Error in query: ' + response.getMessage() + ' ' + response.getDetailedMessage());
            return;
        }

        var data = response.getDataTable();
        drawAreaChart(document.getElementById('stacked_area_chart_div'), data, true,
            'Wait Times - Area Chart Percentage Stacked');
        drawAreaChart(document.getElementById('area_chart_div'), data, false,
            'Wait Times - Area Chart Percentage');
    }

    $(document).ready(function() {
        $(".wt-overall, .wt-platforms").dataTable({
             "bFilter": false,
             "bSort": false,
             "bAutoWidth": false,
             "bPaginate": false,
             "bInfo": false,
        });
    });
</script>
</%def>

<%def name="main_menu()">
  <p>${build_pool_menu(c.report.pool)}</p>
  <p>${datepicker_menu(c.report.starttime, c.report.endtime)}</p>
  <p>Report for <b>${c.report.pool}</b> for jobs submitted between <b>${h.pacific_time(c.report.starttime)}</b> and 
    <b>${h.pacific_time(c.report.endtime)}</b></p>
</%def>

<% wt = c.report %>

<div id="wt-stats">
  <div class="wt-column-s">

    <div class="wt-container">
      <h4>Total Jobs: ${wt.total}</h4>
      <h4>Wait Times</h4>

      <table class="display wt-overall" cellpadding="0" cellspacing="0" border="0">
        <thead><tr><th>Wait Time</th><th>Number</th><th>Percentage</th></tr></thead>
        <tbody>
          % for block in wt.get_blocks():
            <%
            blocklabel = str(block)
            if wt.maxb and block==wt.maxb: blocklabel += '+'
            bval = wt.get_wait_times(block).total
            bper = "%.2f%%" % (bval*100./wt.total) if wt.total else "-"
            %>
            <tr><td>${blocklabel}</td><td>${bval}</td><td>${bper}</td></tr>
          % endfor
        </tbody>
      </table>
    </div>
    
    <br/><br/>
    The number on the <b>Number</b> column is how many minutes a build waited to start, rounded down.<br/><br/>
    <b>Builds with no changes</b> (usually nightly builds): ${wt.no_changes}<br/><br/>
    Rebuilds and forced rebuilds were excluded from the statistics.<br/><br/>
    % if wt.pending:
        Jobs still waiting (have not started yet): ${len(wt.pending)}
        ${more_less_item_list(wt.pending, 'wt-pending-more', 'wt-pending-less')}
    % endif
    % if wt.otherplatforms:
        <b>Other platforms</b> lister under <b>'other'</b> platforms: 
        ${more_less_item_list(list(wt.otherplatforms), 'wt-otherplatforms-more', 'wt-otherplatforms-less')}
    % endif
    % if wt.unknownbuilders:
        <b>Unknown builders</b> (excluded from the stats):
        ${more_less_item_list(list(wt.unknownbuilders), 'wt-unknownbuilders-more', 'wt-unknownbuilders-less')}
    % endif
  </div>

  <div class="wt-column">
    <h4>Platform break down</h4>

    % for platform in sorted(wt.get_platforms()):
      <% ptotal = wt.get_total(platform=platform) %>
    
      <div class="wt-container">
        <div class="wt-container-title">${platform}: ${ptotal}</div>
        <table class="display wt-platforms" cellpadding="0" cellspacing="0" border="0">
          <thead><tr><th>Wait Time</th><th>Number</th><th>Percentage</th></tr></thead>
          <tbody>
            % for block in wt.get_blocks(platform=platform):
              <% bval = wt.get_wait_times(block, platform=platform).total %>
              <% bper = "%.2f%%" % (bval*100./ptotal) if ptotal else "-" %>
              <tr class="gradeA"><td>${block}</td><td>${bval}</td><td>${bper}</td></tr>
            % endfor
          </tbody>
        </table>
      </div>
    % endfor
  </div>

</div>
<div class="clear"></div>

<h2>Area Charts</h2>
<div id="stacked_area_chart_div"></div>
<div id="area_chart_div"></div>
<div id="stacked_area_chart_full_div"></div>
<div id="area_chart_full_div"></div>

<h2>Column Charts</h2>
<div id="stacked_column_chart_full_div"></div>
<dif id="column_chart_full_div"></div>

<h2>Line Charts</h2>
<div id="line_chart_full_div"></div>
