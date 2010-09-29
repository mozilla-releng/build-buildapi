
function drawAreaChart(elem, data, isStacked, title, width, height) {
    var ac = new google.visualization.AreaChart(elem);
    ac.draw(data, {
        title : title || 'Wait Times',
        isStacked: isStacked,
        width: width || 800,
        height: height || 300
    });
}

function drawLineChart(elem, data, isStacked, title, width, height) {
    var cc = new google.visualization.LineChart(elem);
    cc.draw(data, {
        title : title || 'Pushes',
        isStacked: isStacked,
        width: width || 800,
        height: height || 300
    });
}

function drawColumnChart(elem, data, isStacked, title, width, height) {
    var cc = new google.visualization.ColumnChart(elem);
    cc.draw(data, {
        title : title || 'Pushes',
        isStacked: isStacked,
        width: width || 800,
        height: height || 300
    });
}

function drawBarChart(elem, data, isStacked, title, width, height) {
    var cc = new google.visualization.BarChart(elem);
    cc.draw(data, {
        title : title || 'Pushes',
        isStacked: isStacked,
        width: width || 300,
        height: height || 800
    });
}

function drawPieChart(elem, data, title, width, height) {
    var cc = new google.visualization.PieChart(elem);
    cc.draw(data, {
        title : title || '',
        width: width || 450,
        height: height || 300
    });
}
