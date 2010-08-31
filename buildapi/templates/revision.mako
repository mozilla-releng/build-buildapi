<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>List of builds for a revision</title>
${h.tags.javascript_link(
    url('/jquery/js/jquery-1.4.2.min.js'),
    url('/jquery/js/jquery-ui-1.8.1.custom.min.js'),
    url('/DataTables-1.7.1/media/js/jquery.dataTables.min.js'),
    )}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_page.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_table_jui.css')}";
@import "${url('/build-status.css')}";
</style>
<script type="text/javascript">
$(document).ready(function() {
    $("#pending").dataTable({
        "bJQueryUI": true,
        "iDisplayLength": 50,
        "sPaginationType": "full_numbers",
        "aaSorting": [[0,'asc']],
      } );

});

</script>
</head>

<body>
<%
  from datetime import datetime
  now = datetime.now().replace(microsecond=0)
  branch = c.all_builds.keys()[0]
  revision = c.all_builds[branch].keys()[0]
%>
<b>Builds for revision ${revision} in the ${branch} repository.</b>
<div class="demo_jui">
<table id="pending" cellpadding="0" cellspacing="0" border="0" class="display">
<thead>
<tr>
% for key in ('Builder name','Result','Submitted', 'Started','Finished','Waiting/Running/Elapsed','Master'):
<th>${key}</th>
% endfor
</tr></thead><tbody>
% for branch in c.all_builds:
  % for revision in c.all_builds[branch]:
    % for build in c.all_builds[branch][revision]:
      <%
        def GetTime(stamp):
          if stamp is not None:
            return datetime.fromtimestamp(stamp).replace(microsecond=0)
          else:
            return ''
        if 'start_time' not in build:
          build['start_time'] = None
        if 'finish_time' not in build:
          build['finish_time'] = None
        build['submitted_at_human'] = GetTime(build['submitted_at'])
        build['start_time_human'] = GetTime(build['start_time'])
        build['finish_time_human'] = GetTime(build['finish_time'])
        if build['start_time'] is None:
          build['time'] = now - datetime.fromtimestamp(build['submitted_at'])
          build['state'] = 'pending'
        elif build['finish_time'] is None:
          build['time'] = now - datetime.fromtimestamp(build['start_time'])
          build['state'] = 'running'
        else:
          build['time'] = datetime.fromtimestamp(build['finish_time']) - datetime.fromtimestamp(build['start_time'])
          build['state'] = 'result%s' % build['results']
        if build['claimed_by_name']:
          build['master'] = build['claimed_by_name'].split('.')[0]
          if build['master'].startswith(('talos-master02','test-master0')):
            port = '8012'
          elif 'try' in branch:
            port = '8011'
          else:
            port = '8010'
          build['url'] = 'http://%s:%s/builders/%s/builds/%s' % \
                         (build['claimed_by_name'].split(':')[0],
                          port,
                          build['buildername'].replace('/','%2F'),
                          build['number'])
      %>
      <tr>
      % for key in ('buildername','results','submitted_at_human','start_time_human','finish_time_human','time','master'):
        % if key == 'revision':
          <td>${build[key][0:12]}</td>
        % elif key == 'master':
           % if 'master' in build:
             <td><a href="${build['url']}">${build['master']}</a></td>
           % else:
             <td>Pending</td>
           % endif
        % elif key == 'results':
          <td class="${build['state']}">${build['results']}</td>
        % else:
          <td>${build[key]}</td>
        % endif
      % endfor
      </tr>
    % endfor
  % endfor
%endfor
</tbody><table>

</body>
</html>
Generated at ${now}. All times are Mountain View, CA (US/Pacific).
