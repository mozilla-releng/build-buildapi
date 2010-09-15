<%def name="print_datetime_short(timestamp)">
  <% dt_format = '%m/%d/%y %H:%M:%S' %>
  ${h.pacific_time(timestamp, format=dt_format) if timestamp else '-'}
</%def>

<%def name="print_datetime(timestamp)">
  ${h.pacific_time(timestamp) if timestamp else '-'}
</%def>

<%def name="link_menu(selitem, itemlist, item_link_func)"> 
  % for item in itemlist:
      % if item == selitem:
          <b>${item}</b> | 
      % else:
          <a href="${item_link_func(item)}">${item}</a> | 
      % endif
  % endfor
</%def>

<%def name="build_pool_menu(pool)">
  <%
    from buildapi.model.util import BUILDPOOL_MASTERS
    params = dict(request.params)
    if 'pool' in params: del params['pool']

    pool_list = sorted(BUILDPOOL_MASTERS.keys())
    pool_link_func = lambda x: url.current(pool=x, **params)
  %>

  Build pool: ${link_menu(pool, pool_list, pool_link_func)}
</%def>

<%def name="branch_menu(branch)">
  <%
    from buildapi.model.util import SOURCESTAMPS_BRANCH
    params = dict(request.params)
    if 'branch' in params: del params['branch']

    branch_list = sorted(SOURCESTAMPS_BRANCH.keys())
    branch_link_func = lambda x: url.current(branch_name=x, **params)
  %>

  Branch: ${link_menu(branch, branch_list, branch_link_func)}
</%def>

<%def name="reports_menu()">
  <%
  report_url_mapper = {
     'Average Time per Builder': url.current(action='builders', branch_name=None, pool=None),
     'End to End Times': url.current(action='endtoend', branch_name=None, pool=None),
     'Pushes': url.current(action='pushes', branch_name=None, pool=None),
     'Wait Times': url.current(action='waittimes', branch_name=None, pool=None),
  }  
  report_link_func = lambda x: report_url_mapper[x]
  %>

  Reports: ${link_menu(None, sorted(report_url_mapper.keys()), report_link_func)}
</%def>

<%def name="datepicker_menu(starttime, endtime)">
  <label for="starttime">Jobs submitted between</label>
  <input type="text" id="starttime" size="26" value="" ref="${starttime}"/>
  <label for="endtime2">and</label>
  <input type="text" id="endtime" size="26" value="" ref="${endtime}"/>
  <input type="button" id="timeIntervalButton" value="Go!"/>
  <script type="text/javascript">
      $(document).ready(function() {
          initDatePicker($("#starttime"));
          initDatePicker($("#endtime"));
          $("#timeIntervalButton").click(updateWindowLocation);
      });
  </script>
</%def>

<%def name="more_less_item_list(itemlist, id_more, id_less)">
  <div id="${id_less}"><ul>
    % for item in itemlist[:5]:
      <li>${item}</li>
    % endfor
  </ul><a href="">more...</a></div>
  <div id="${id_more}" style="display:none"><ul>
    % for item in itemlist:
      <li>${item}</li>
    % endfor
  </ul><a href="">less...</a></div><br/>
  <script type="text/javascript">
      $(document).ready(function() {
          initToggleBoxes('#' + id_mode, '#' + id_less);
      });
  </script>
</%def>
