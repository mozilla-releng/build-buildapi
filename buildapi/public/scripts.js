
function initDatePickers() {
    var starttime = $('#starttime').attr('ref');  // start time in PDT (server time) in seconds
    var endtime = $('#endtime').attr('ref');      // end time in PDT (server time) in seconds
    var sdate = parseDatePickerDate(starttime);
    var edate = parseDatePickerDate(endtime);

    // set initial values
    $('#starttime').datepicker("setDate", sdate);
    $('#endtime').datepicker("setDate", edate);
}

function updateWindowLocation() {
    // get unix time in seconds
    var url = window.location.href.split('?')[0];
    var q = window.location.search;
    q = ((q.length>=1)&&(q[0]=='?'))?q.substr(1):q;  // remove ? character

    var sdate = $('#starttime').datepicker("getDate");
    var edate = $('#endtime').datepicker("getDate");
    var starttime = $.datepicker.formatDate('@', sdate) / 1000;
    var endtime = $.datepicker.formatDate('@', edate) / 1000;

    var new_q = ['starttime='+starttime, 'endtime='+endtime];
    var params = q.split('&');
    for (var i in params) {
        var key = params[i].split('=')[0];
        if (key!='starttime' && key!='endtime') {
            new_q.push(params[i]);
        }
    }

    window.location = url + '?' + new_q.join('&');
}

function parseDatePickerDate(unix_time_sec) {
    if (!unix_time_sec) return null;
    var unix_time_mili = parseInt(parseFloat(unix_time_sec) * 1000);
    var date = $.datepicker.parseDate('@', unix_time_mili);

    return date;
}
