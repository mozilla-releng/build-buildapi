var AnyTime_picker_format = "%a, %d %b %z %H:%i:%s %+";
var AnyTime_conv = new AnyTime.Converter({format: AnyTime_picker_format});

function initAnyTimePickers() {
    var starttime = $('#starttime').attr('ref');  // start time in UTC in seconds
    var endtime = $('#endtime').attr('ref');      // end time in UTC in seconds

    var sdate = new Date(parseFloat(starttime)*1000);
    var edate = new Date(parseFloat(endtime)*1000);

    // set initial values
    $("#starttime").val(AnyTime_conv.format(sdate));
    $("#endtime").val(AnyTime_conv.format(edate));
}

function updateWindowLocation() {
	var sdate = AnyTime_conv.parse($('#starttime').val());
    var edate = AnyTime_conv.parse($('#endtime').val());    
    var starttime = parseFloat(sdate.getTime()) / 1000;
    var endtime = parseFloat(edate.getTime()) / 1000;

    var new_params = {starttime: starttime, endtime: endtime};
    window.location = updateUrlParams(new_params);
}

function updateUrlParams(new_params) {
    var url = window.location.href.split('?')[0];
    var q = window.location.search;
    q = ((q.length>=1)&&(q[0]=='?'))?q.substr(1):q;  // remove ? character

    var params = q.split('&');
    for (var i in params) {
	    if (!params[i]) continue;
        var p = params[i].split('=');
        var key = p[0], val = p[1];
        if (!(key in new_params)) { new_params[key] = val; }
    }
    var new_q = [];
	for (key in new_params) {
        new_q.push(key+'='+new_params[key]);
    }

    return url + '?' + new_q.join('&');
}
