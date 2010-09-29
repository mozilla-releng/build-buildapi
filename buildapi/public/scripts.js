var datepicker_format = "mm/dd/yy";

function initDatePicker(elem) {
    // create datepicker element
    elem.datepicker();
    // get timestamp from element's attribute
    var timestamp = elem.attr('ref');    // start time in UTC in seconds
    var date = new Date(parseFloat(timestamp)*1000);
    // set initial velue
    elem.val($.datepicker.formatDate(datepicker_format, date));
}

function updateWindowLocation() {
    var sdate = $.datepicker.parseDate(datepicker_format, $('#starttime').val());
    var edate = $.datepicker.parseDate(datepicker_format, $('#endtime').val());
    var sdate_ms = sdate.getTime();
    var edate_ms = edate.getTime();
    var starttime = parseFloat(sdate_ms) / 1000;
    var endtime = parseFloat(edate_ms) / 1000;

    var new_params = {starttime: starttime, endtime: endtime};
    window.location = updateUrlParams(new_params);
}

function parseUrlParams(url) {
    var q = url ? (url.split('?')[1] || '') : window.location.search;
    q = ((q.length>=1)&&(q[0]=='?'))?q.substr(1):q;  // remove ? character

    var params = q.split('&');
    var params_dict = {};
    for (var i in params) {
        if (!params[i]) continue;
        var p = params[i].split('=');
        var key = p[0], val = p[1];
        params_dict[key] = val;
    }

    return params_dict;
}

function parseUrlBase(url) {
    return (url || window.location.href).split('?')[0];
}

function updateUrlParams(new_params, url) {
    var params = parseUrlParams(url);
    var baseUrl = parseUrlBase(url);
    for (var key in params) {
        if (!params[key]) continue;
        if (!(key in new_params)) { new_params[key] = params[key]; }
    }
    var new_q = [];
    for (key in new_params) {
        new_q.push(key+'='+new_params[key]);
    }

    return baseUrl + '?' + new_q.join('&');
}

function initToggleBoxes(id1, id2, button_id1, button_id2) {
    var button_id1 = button_id1 || id1 + " a";
    var button_id2 = button_id2 || id2 + " a";
    $(button_id1 + " , " + button_id2).click(function() {
       $(id1).toggle();
       $(id2).toggle();

       return false;
    });
}
