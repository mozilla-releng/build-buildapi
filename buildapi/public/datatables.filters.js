(function($) {
    $.fn.dataTableExt.oApi.fnGetFilteredColumnSum = function(oSettings, iCol) {
        // get total run_time sum for currently visible rows (after filtering)
        var fsum = 0;
        var fData = this.fnGetFilteredData();
        for (var i = 0; i < fData.length; i++) {
            fsum += parseInt(fData[i][iCol]);
        }
        return fsum;
    };

    $.fn.dataTableExt.oApi.fnUpdatePtgColumn = function(oSettings, iSumCol, iPtgCol) {
        var fsum = this.fnGetFilteredColumnSum(iSumCol);
        var oDisplay = oSettings.aiDisplay;
        for (var i = 0; i < oDisplay.length; i++) {
            var mRow = oDisplay[i];
            var rowData = oSettings.aoData[mRow]._aData;
            var ptg = (parseFloat(rowData[iSumCol]) / fsum * 100).toFixed(2);
            this.fnUpdate(ptg, mRow, iPtgCol, false, false);
        }
    };

    function Filters(filters, elem, options) {
        this.filters = filters;
        this.elem = elem;
        this.options = $.extend({}, Filters.defaults, options);

        this.attachOnChangeEvents();
        this.domUpdate();
    };

    Filters.prototype.getFilter = function(filterName) {
        return this.filters[filterName];
    }

    Filters.prototype.getLink = function() {
        var new_params = {};
        for (var fn in this.filters) {
           new_params[fn] = this.filters[fn].join(',');
        }
        var link = updateUrlParams(new_params);
        return link;
    };

    Filters.prototype.setFilter = function(filterName, checkedList) {
        this.filters[filterName] = checkedList;
    };

    Filters.prototype.domUpdate = function() {
       for (var fn in this.filters) {
          this.domUpdateFilter(fn, this.filters[fn]);
       }
       this.domUpdateLink();
    };

    Filters.prototype.domUpdateFilter = function(filterName, checkedList) {
       var selector = this.getFilterSelector(filterName);
       var checked = checkedList;
       var markChecked = function() {
           var value = $(this).attr("value");
           if (checked.length == 0 || checked.indexOf(value) != -1) {
               $(this).attr("checked", "checked");
           } else {
               $(this).attr("checked",  "");
           }
       }
       $(selector).each(markChecked);
    };

    Filters.prototype.domUpdateLink = function() {
        $(this.options.linkSelector, $(this.elem)).val(this.getLink());
    };

    Filters.prototype.domParseCheckedValues = function(filterName) {
        var f = [];
        var selector = this.getFilterSelector(filterName);
        $(selector).each(function() {
            if ($(this).attr('checked')) {
                f.push($(this).val());
            }});
        return f;
    };

    Filters.prototype.attachOnChangeEvents = function() {
        for (var fn in this.filters) {
            var _that = this;
            var selector = this.getFilterSelector(fn);
            $(selector).click(function() {
                var filterName = $(this).attr('name');
                var checkedList = _that.domParseCheckedValues(filterName);

                _that.setFilter(filterName, checkedList);
                _that.domUpdateLink();
                _that.options.onChangeCallback(filterName, checkedList);
            });
        }
    };

    Filters.prototype.getFilterSelector = function(filterName) {
        return $("input[name='" + filterName + "']", $(this.elem));
    };

    Filters.defaults = {
        linkSelector: ".link",
        onChangeCallback: function() {},
    };

    $.fn.filters = function(filters, options) {
        new Filters(filters, $(this), options);
        return $(this);
    };

    function BuildersTableFiltersWrapper(oTable, options) {
        this.options = $.extend({}, BuildersTableFiltersWrapper.defaults, options);
        this.oTable = oTable;
    };

    BuildersTableFiltersWrapper.prototype.updatePtgColumn = function() {
        var sumCol = this.options.sumRunTimeCol;
        var ptgCol = this.options.ptgRunTimeCol;
        this.oTable.fnUpdatePtgColumn(sumCol, ptgCol);
    };

    BuildersTableFiltersWrapper.prototype.applyFilters = function(filters) {
        for (var fn in filters) {
            this.applyFilter(fn, filters[fn]);
        }
        this.updatePtgColumn();
        var chartData = this.parsePtgRunTimeChartData();
        updatePieChart(document.getElementById('piechart'), chartData);
    };

    BuildersTableFiltersWrapper.prototype.applyFilter = function(filterName, checkedList) {
        var iCol = this.options.tableFilterCols[filterName];
        var rgex_filter = '^(' + checkedList.join('|') + '|)$';
        this.oTable.fnFilter(rgex_filter, iCol, true, false);
    };

    BuildersTableFiltersWrapper.prototype._fnGetRowBuilderName = function(rowData) {
        var p = this.options.platformCol;
        var bt = this.options.buildTypeCol;
        var jt = this.options.jobTypeCol;
        var b = this.options.buildernameCol;

        // get buildername from platform, buildType, jobType and buildername columns
        var sname = [rowData[p], rowData[bt], rowData[jt], rowData[b]];
        return sname.join(' ');
    };

    BuildersTableFiltersWrapper.prototype.parsePtgRunTimeChartData = function() {
         var chartData = [];
         var oSettings = this.oTable.fnSettings();
         var oDisplay = oSettings.aiDisplay;
         for (var i = 0; i < oDisplay.length; i++) {
             var rowData = oSettings.aoData[oDisplay[i]]._aData;
             var ptg = rowData[this.options.ptgRunTimeCol];

             // set chart data values
             var name = this._fnGetRowBuilderName(rowData);
             chartData.push({name: name, value: parseFloat(ptg)})
        }

        return chartData;
    };

    BuildersTableFiltersWrapper.defaults = {
        tableFilterCols: {platform: 1, build_type: 2, job_type: 3, detail_level: 0},
        platformCol: 1,
        buildTypeCol: 2,
        jobTypeCol: 3,
        buildernameCol: 4,
        ptgRunTimeCol: 5,
        sumRunTimeCol: 6,
    };

    $.fn.dataTableExt.oApi.fnCreateFilterWrapper = function(oSettings, options) {
        return new BuildersTableFiltersWrapper(this, options);
    };
})(jQuery);

function parseFiltersFromUrl(filterNames) {
    var f = {};
    var params = parseUrlParams();
    for (var i = 0; i < filterNames.length; i++) {
        var fn = filterNames[i];
        var values = [];    // set default value
        if (fn == 'detail_level') {
            values = ['builder'];   // set default value
        }
        if (fn in params && params[fn]) {
            values = params[fn].split(',');
        }
        f[fn] = values;
    }
    return f;
}

function updatePieChart(elem, chartData) {
    // chart data init
    var data = new google.visualization.DataTable();
    data.addColumn('string', 'Builder');
    data.addColumn('number', 'Run Time');
    data.addRows(chartData.length);

    chartData.sort(function(a, b) { return b['value'] - a['value'];});
    for (var i=0; i<chartData.length; i++) {
        data.setValue(i, 0, chartData[i]['name']);
        data.setValue(i, 1, chartData[i]['value']);
    }

    drawPieChart(elem, data);
}
