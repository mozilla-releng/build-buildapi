<%def name="print_datetime_short(timestamp)">
  <% dt_format = '%m/%d/%y %H:%M:%S' %>
  ${h.pacific_time(timestamp, format=dt_format) if timestamp else '-'}
</%def>

<%def name="print_datetime(timestamp)">
  ${h.pacific_time(timestamp) if timestamp else '-'}
</%def>

<%def name="link_menu(selitem, itemlist, item_link_func, item_label_func=lambda x: x)"> 
  % for item in itemlist:
      % if item == selitem:
          <b>${item_label_func(item)}</b> | 
      % else:
          <a href="${item_link_func(item)}">${item_label_func(item)}</a> | 
      % endif
  % endfor
</%def>

<%def name="select_menu(id, selitem, itemlist)"> 
  <select name="${id}">
    % for item in itemlist:
      % if item == selitem:
        <option value="${item}" selected="selected">${item}</option>
      % else:
        <option value="${item}">${item}</option>
      % endif
    % endfor
  </select>
</%def>

<%def name="build_pool_menu(pool)">
  <%
    from buildapi.model.util import POOLS
    params = dict(request.params)
    if 'pool' in params: del params['pool']

    pool_list = sorted(POOLS)
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

<%def name="branch_select_menu(id, branch)">
  <% from buildapi.model.util import SOURCESTAMPS_BRANCH %>
  ${select_menu(id, branch, sorted(SOURCESTAMPS_BRANCH.keys()))}
</%def>

<%def name="buildrun_search_menu(id, revision, branch)">
  <div id="${id}">Jump to Build Run Report for revision 
    <input name="revision" type="text" value="${revision}" />, branch
    ${branch_select_menu("branch", branch)}
    <input type="button" value="Go!" onclick="goToBuildRun();" />
  </div>

  <script type="text/javascript">
      function goToBuildRun() {
          var rev = $("#${id} input[name=revision]")[0].value;
          rev.replace(/\s/g, "");
          rev = rev.substring(0, 12);
          var branch = $("#${id} select[name=branch]")[0].value;

          window.location = "/reports/revision/" + branch + "/" + rev;
      }
  </script>
</%def>

<%def name="reports_menu()">
  <%
  params = dict(buildername=None, branch_name=None, pool=None, revision=None, 
      slave_id=None, builder_name=None)
  report_url_mapper = {
     'Average Time per Builder': url.current(action='builders', **params),
     'Builders' : url.current(action='status_builders', **params),
     'End to End Times': url.current(action='endtoend', **params),
     'Pushes': url.current(action='pushes', **params),
     'Slaves' : url.current(action='slaves', **params),
     'Wait Times': url.current(action='waittimes', **params),
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
          initToggleBoxes('#${id_more}', '#${id_less}');
      });
  </script>
</%def>

<%def name="checkbox_menu(name, itemlist, checkedlist)">
  <span class="check_list ${name}">
    % for item in itemlist:
      <% ch = 'checked' if item in checkedlist else '' %>
      <input type="checkbox" name="${name}" value="${item}" checked="${ch}" /> ${item}
    % endfor
  </span>
</%def>

<%def name="radio_menu(name, itemlist, checked)">
  <span class="check_list ${name}">
    % for item in itemlist:
      <% ch = 'checked' if item == checked else '' %>
      <input type="radio" name="${name}" value="${item}" checked="${ch}" /> ${item}
    % endfor
  </span>
</%def>

<%def name="builders_table_filters_menu(id)">
  <%! from buildapi.model.util import PLATFORMS_BUILDERNAME, BUILD_TYPE_BUILDERNAME, JOB_TYPE_BUILDERNAME, BUILDERS_DETAIL_LEVELS %>
  <div id="${id}">
    <p>
      <b>Filters:</b>
      <br/><i>Platform:</i>
      <% platforms = sorted(PLATFORMS_BUILDERNAME.keys()) %>
      ${checkbox_menu('platform', platforms, [])}

      <br/><i>Build Type:</i>
      <% build_type = sorted(BUILD_TYPE_BUILDERNAME.keys()) %>
      ${checkbox_menu('build_type', build_type, [])}

      <br/><i>Job Type:</i>
      <% job_type = sorted(JOB_TYPE_BUILDERNAME.keys()) %>
      ${checkbox_menu('job_type', job_type, [])}
    <br/></p>
    <p>
      <b>Detail level:</b>
      <% 
      dl = BUILDERS_DETAIL_LEVELS 
      checked = dl[-1] if len(dl) else 0 %>
      ${radio_menu('detail_level', dl, checked)}
    </p>
    Link: <input type="text" class="link" readonly="readonly" size="120"/>
  </div>
</%def>

<%def name="int_size_menu()">
  <span>
    <%
    intervals = [('minute', 60), ('hour', 3600), ('day', 86400),
        ('week', 604800), ('month (30 days)', 2592000)]
    params = dict(request.params)
    if 'int_size' in params:
        size = params['int_size']
        del params['int_size']
    int_size_link_func = lambda x: url.current(int_size=intervals[x][1], **params)
    int_size_label_func = lambda x: intervals[x][0]
    %>

    Int size: ${link_menu(None, xrange(len(intervals)), int_size_link_func, 
        item_label_func=int_size_label_func)}
  </span>
</%def>
