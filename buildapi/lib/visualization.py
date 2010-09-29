import time
import gviz_api

def gviz_waittimes(report, num='full', resp_type='JSonResponse', req_id='0'):
    """Transforms Wait Times Report to Google Visualization API Data Table, 
    and returns it either as JSONResponse or JSCode objects.

    Input: num - the type of values, either 'full' for total number per 
                interval, or 'ptg' for percentages
           rep_type - type of returned value (e.g. JSonResponse or JSCode)
    Output: JSONResponse or JSCode Visualization API objects
    """
    intervals = [
        time.strftime('%m/%d %H:%M',
            time.localtime(report.get_interval_timestamp(t)))
        for t in range(report.int_no)]
    blocks = report.get_blocks()

    # compute total sourcestamps on each interval and block number
    int_totals = [0] * report.int_no
    for i in range(report.int_no):
        for block_no in blocks:
            int_totals[i] += report.get_wait_times(block_no).intervals[i]

    # gviz table description (columns)
    description = {'intervals': ('string', 'Interval')}
    for block_no in blocks: 
        collabel = str(block_no) + '-' + str(block_no + report.mpb)
        if report.maxb and block_no == report.maxb:
            collabel = str(block_no) + '+'
        description[str(block_no)] = ('number', collabel)

    # gviz table data (rows)
    data = []
    for i in range(len(intervals)):
        row = {'intervals': intervals[i]}
        for block_no in blocks:
            int_val = report.get_wait_times(block_no).intervals[i]
            if num == 'ptg':
                int_total = int_totals[i]
                row[str(block_no)] = (int_val * 100. / int_total) if int_total else 0
            else: 
                row[str(block_no)] = int_val 
        data.append(row)

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)
    
    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=tuple(['intervals'] + map(str, blocks)))
    else:
        return data_table.ToJSonResponse(req_id=req_id, 
            columns_order=tuple(['intervals'] + map(str, blocks)))

def gviz_pushes(report, resp_type='JSonResponse', req_id='0'):
    """Transforms Pushes Report to Google Visualization API Data Table, and 
    returns it either as JSONResponse or JSCode objects.

    Input: rep_type - type of returned value (e.g. JSonResponse or JSCode) 
    Output: JSONResponse or JSCode Visualization API objects
    """
    intervals = [
        time.strftime('%m/%d %H:%M', 
            time.localtime(report.get_interval_timestamp(t))) 
        for t in range(report.int_no)]

    # gviz table description (columns)
    description = {'intervals': ('string', 'Interval'), 'totals': ('number', 'Totals')}
    for branch in report.branch: description[branch] = ('number', branch)

    # gviz table data (rows)
    data = []
    for i in range(report.int_no):
        row = {'intervals': intervals[i], 'totals': report.get_intervals()[i]}
        for branch in report.branch:
            row[branch] = report.get_intervals(branch=branch)[i]

        data.append(row)

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=tuple(['intervals', 'totals'] + sorted(report.branch)))
    else:
        return data_table.ToJSonResponse(req_id=req_id,
            columns_order=tuple(['intervals', 'totals'] + sorted(report.branch)))

def gviz_builders(report, resp_type='JSonResponse', req_id='0'):
    """Transforms Builders Report to Google Visualization API Data Table with 
    run times per each builder, and returns it either as JSONResponse or 
    JSCode objects.

    Input: rep_type - type of returned value (e.g. JSonResponse or JSCode)
    Output: JSONResponse or JSCode Visualization API objects
    """
    # gviz table description (columns)
    description = {
        'builder': ('string', 'Builder'), 
        'run_time': ('number', 'Run Time')
    }

    # gviz table data (rows)
    data = []
    total_sum_run_time = report.builders.info.get_sum_run_time()
    for b in report.get_builders(leafs_only=True):
        buildername = ' '.join(report.get_path(b))
        ptg_run_time = float("%.2f" % \
            (b.get_sum_run_time()*100. / total_sum_run_time if total_sum_run_time else 0))
        row = {'builder': buildername, 'run_time': ptg_run_time}

        data.append(row)

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=('builder', 'run_time'), order_by='run_time')
    else:
        return data_table.ToJSonResponse(req_id=req_id, 
            columns_order=('builder', 'run_time'), order_by='run_time')

def gviz_trychooser_authors(report, resp_type='JSonResponse', req_id='0'):
    # gviz table description (columns)
    description = {
        'trychooser': ('string', 'Authors Used TryChooser'), 
        'ptg': ('number', 'Percentage')
    }

    # gviz table data (rows)
    data = [
        {'trychooser': 'Yes', 'ptg': len(report.get_used_trychooser())},
        {'trychooser': 'No', 'ptg': len(report.get_not_used_trychooser())},
    ]

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data_authors",
            columns_order=('trychooser', 'ptg'), order_by='trychooser')
    else:
        return data_table.ToJSonResponse(req_id=req_id, 
            columns_order=('trychooser', 'ptg'), order_by='trychooser')

def gviz_trychooser_runs(report, resp_type='JSonResponse', req_id='0'):
    # gviz table description (columns)
    description = {
        'trychooser': ('string', 'Runs Used TryChooser'),
        'ptg': ('number', 'Percentage')
    }

    # gviz table data (rows)
    data = [
        {'trychooser': 'Yes', 'ptg': report.get_runs_used_trychooser()},
        {'trychooser': 'No', 'ptg': 
            report.get_total_build_runs() - report.get_runs_used_trychooser()},
    ]

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data_runs",
            columns_order=('trychooser', 'ptg'), order_by='trychooser')
    else:
        return data_table.ToJSonResponse(req_id=req_id, 
            columns_order=('trychooser', 'ptg'), order_by='trychooser')
