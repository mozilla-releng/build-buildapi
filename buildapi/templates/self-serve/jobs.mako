<%inherit file="/base.mako" />
<%def name="title()">RelEng Self-Serve API - Job History</%def>
<%def name="header()">
<script type="text/javascript">
$(document).ready(function()
{
    var options = {
        bJQueryUI: true,
        sPaginationType: "full_numbers"
    }
    $("#jobs").dataTable(options);
})
</script>
</%def>
<%def name="body()">\
<table id="jobs">
<thead>
<tr><th>Who</th><th>What</th><th>When</th><th>Completed at</th><th>Results</th></tr>
</thead>
<tbody>
% for job in c.data:
    <tr><td>${job['who']}</td>
        <td>${job['action']} <pre>${job['what']}</pre></td>
        <td>${self.attr.formattime(job['when'])}</td>
        <td>${self.attr.formattime(job['completed_at'])}</td>
        <td><pre>${job['complete_data']}</pre></td>
    </tr>
% endfor
</tbody>
</table>
</%def>
