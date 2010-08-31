<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>${self.title()}</title>
${h.tags.javascript_link(
    url('/jquery/js/jquery-1.4.2.min.js'),
    url('/jquery/js/jquery-ui-1.8.1.custom.min.js'),
    url('/DataTables-1.7.1/media/js/jquery.dataTables.min.js'),
    url('/scripts.js'),
    url('/gviz.js'),
)}
<style type="text/css">
@import "${url('/jquery/css/smoothness/jquery-ui-1.8.1.custom.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_page.css')}";
@import "${url('/DataTables-1.7.1/media/css/demo_table_jui.css')}";
@import "${url('/build-status.css')}";
</style>

${self.head()}
</head>

<body id="dt_example">
  <h1>${self.title()}</h1>

  <div class="main-menu">
    ${self.main_menu()}
  </div>

  ${self.body()}
  ${self.footer()}
</body>
</html>

<%def name="footer()">
  <br/>Generated at ${h.pacific_time(None)}.
</%def>

<%def name="title()">Report</%def>

<%def name="main_menu()"></%def>
