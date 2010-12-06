<%inherit file="report.mako"/>
<%namespace file="util.mako" import="buildrun_search_menu"/>

<%def name="title()">Build Run Report</%def>

<%def name="head()"></%def>

<%def name="main_menu()">
  ${buildrun_search_menu("buildrun_jump", "", "mozilla-central")}
</%def>
