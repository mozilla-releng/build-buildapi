import time
from datetime import datetime
import gviz_api
from buildapi.model.util import SUCCESS, WARNINGS, FAILURE

def gviz_idlejobs(report, resp_type='JSonResponse'):
    """Transforms idlejobs report into a google visualization data table, and 
    returns it as either JSON or JSCode.

    Input: report, resp_type
    Output: JSON/JSCode of resulting data table
    """
    intervals = [
        time.strftime('%m/%d %H:%M',
            time.localtime(report.get_interval_timestamp(t)))
        for t in xrange(report.int_no)]

    description = {'intervals': ('string', 'Interval'),}
    for builder in report.builders:
        description[builder] = ('number', builder)

    data = []
    for i in xrange(report.int_no):
        row = { 'intervals': intervals[i], }
        for builder in report.builders:
            row[builder] = int(report.builder_intervals[builder][i])
        data.append(row)

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=tuple(['intervals'] + sorted(report.builders)))
    else:
        return data_table.ToJSonResponse(
            columns_order=tuple(['intervals'] + sorted(report.builders)))
 
def gviz_testruns(report, resp_type='JSonResponse'):
    """Transforms testrun report into a Google visualization API Data Table, 
    and returns it either as JSONResponse or JSCode objects.

    Inputs: report, resp_type - type of object to return (JSONResponse/JSCODE)
    Output: JSONResponse/JSCode Visualization API objects
    """
    description = {'builders': ('string', 'Builder'),
                   'setup': ('number', 'Setup/Teardown Time'),
                   'test':('number', 'Test Run Time')}

    data = []
    for builder in report.builders:
        row = {
            'builders': builder, 
            'setup': int(report.builders[builder]['total'] - 
                report.builders[builder]['test']), 
            'test': int(report.builders[builder]['test'])
        }
        data.append(row)

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=('builders', 'setup', 'test'))
    else:
        return data_table.ToJSonResponse(
            columns_order=('builders', 'setup', 'test'))

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
        for t in xrange(report.int_no)]
    blocks = report.get_blocks()

    # compute total sourcestamps on each interval and block number
    int_totals = [0] * report.int_no
    for i in xrange(report.int_no):
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
    for i in xrange(len(intervals)):
        row = {'intervals': intervals[i]}
        for block_no in blocks:
            int_val = report.get_wait_times(block_no).intervals[i]
            if num == 'ptg':
                int_total = int_totals[i]
                row[str(block_no)] = (int_val * 100. / int_total) \
                    if int_total else 0
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
    # gviz table description (columns)
    description = {
        'branch': ('string', 'Branch'), 
        'totals': ('number', '# Pushes')
    }

    # gviz table data (rows)
    data = []
    for branch in report.branches:
        totals = report.get_total(branch=branch)
        data.append({'branch': branch, 'totals': totals})

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=('branch', 'totals'))
    else:
        return data_table.ToJSonResponse(req_id=req_id,
            columns_order=('branch', 'totals'))

def gviz_pushes_daily_intervals(report, resp_type='JSonResponse', req_id='0'):
    """Transforms Pushes Report Average # of Pushes per Hour to Google 
    Visualization API Data Table, and returns it either as JSONResponse or 
    JSCode objects.

    Input: rep_type - type of returned value (e.g. JSonResponse or JSCode) 
    Output: JSONResponse or JSCode Visualization API objects
    """
    # gviz table description (columns)
    description = {
        'hour': ('string', 'Hour'),
        'average': ('number', 'Average # Pushes per Hour')
    }

    # gviz table data (rows)
    data = []
    for int_no in xrange(len(report.daily_intervals)):
        avg = report.daily_intervals[int_no] / report.days
        data.append({
            'hour': '%02d' % int_no,
            'average': avg,
        })

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=('hour', 'average'))
    else:
        return data_table.ToJSonResponse(req_id=req_id,
            columns_order=('hour', 'average'))

def gviz_pushes_intervals(report, resp_type='JSonResponse', req_id='0'):
    """Transforms Pushes Report per Intervals to Google Visualization API 
    Data Table, and returns it either as JSONResponse or JSCode objects.

    Input: rep_type - type of returned value (e.g. JSonResponse or JSCode) 
    Output: JSONResponse or JSCode Visualization API objects
    """
    intervals = [
        time.strftime('%m/%d %H:%M', 
            time.localtime(report.get_interval_timestamp(t)))
        for t in xrange(report.int_no)]

    # gviz table description (columns)
    description = {'intervals': ('string', 'Interval'),
        'totals': ('number', 'Totals')}
    for branch in report.branches:
        description[branch] = ('number', branch)

    # gviz table data (rows)
    data = []
    for i in xrange(report.int_no):
        row = {'intervals': intervals[i], 'totals': report.get_intervals()[i]}
        for branch in report.branches:
            row[branch] = report.get_intervals(branch=branch)[i]

        data.append(row)

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=tuple(['intervals', 'totals'] + sorted(report.branches)))
    else:
        return data_table.ToJSonResponse(req_id=req_id,
            columns_order=tuple(['intervals', 'totals'] + sorted(report.branches)))

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
            (b.get_sum_run_time()*100. / total_sum_run_time
                if total_sum_run_time else 0))
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

def gviz_slaves(report, resp_type='JSonResponse', req_id='0'):
    """Returns the Visualization API Data Table containing the percentage of 
    successful vs. warnings vs. failing builds for a slave over a timeframe 
    based on the SlaveDetailsReport.

    Input: SlaveDetailsReport, resp_type
    Output: JSON/JSCode of resulting data table
    """
    # gviz table description (columns)
    description = {
        'datetime': ('datetime', 'Date'),
        'success': ('number', 'Success'),
        'warnings': ('number', 'Warnings'),
        'failed': ('number', 'Failed'),
    }

    # gviz table data (rows)
    data = []
    intervals = [
        datetime.fromtimestamp(report.get_interval_timestamp(t)) 
        for t in xrange(report.int_no)]

    results = report.get_ptg_int_results()
    succ = results[SUCCESS]
    warn = results[WARNINGS]
    fail = results[FAILURE]
    for idx in xrange(report.int_no):
        row = {
            'datetime': intervals[idx],
            'success': succ[idx],
            'warnings': warn[idx],
            'failed': fail[idx],
        }
        data.append(row)

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=('datetime', 'success', 'warnings', 'failed'))
    else:
        return data_table.ToJSonResponse(req_id=req_id, 
            columns_order=('datetime', 'success', 'warnings', 'failed'))

def gviz_slaves_busy(report, resp_type='JSonResponse', req_id='0'):
    """Returns the Visualization API Data Table containing the activity 
    intervals (running builds) and their type (success/warning/failure) over 
    a timeframe, based on the SlaveDetailsReport.

    Input: SlaveDetailsReport, resp_type
    Output: JSON/JSCode of resulting data table
    """
    # gviz table description (columns)
    description = {
        'datetime': ('datetime', 'Date'),
        'success': ('number', 'Busy Success'),
        'warnings': ('number', 'Busy Warnings'),
        'failure': ('number', 'Busy Failure'),
    }

    # gviz table data (rows)
    data = []
    for stime, etime, result in sorted(report.busy):
        # preinterval, set 0
        pre_int_left = { 
            'datetime': datetime.fromtimestamp(stime - 1),
            'success': 0,
            'warnings': 0,
            'failure': 0
        }
        # interval, left side, set 1
        int_left = { 
            'datetime': datetime.fromtimestamp(stime),
            'success': 1 if result == SUCCESS else 0,
            'warnings': 1 if result == WARNINGS else 0,
            'failure': 1 if result == FAILURE else 0,
        }
        data.extend([pre_int_left, int_left])

        if etime:
            # interval, right side, set 1
            int_right = { 
                'datetime': datetime.fromtimestamp(etime),
                'success': 1 if result == SUCCESS else 0,
                'warnings': 1 if result == WARNINGS else 0,
                'failure': 1 if result == FAILURE else 0,
            }
            # postinterval, set 0
            post_int_right = {
                'datetime': datetime.fromtimestamp(etime + 1),
                'success': 0,
                'warnings': 0,
                'failure': 0
            }
            data.extend([int_right, post_int_right])

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=('datetime', 'success', 'warnings', 'failure'))
    else:
        return data_table.ToJSonResponse(req_id=req_id, 
            columns_order=('datetime', 'success', 'warnings', 'failure'))

def gviz_slaves_int_busy(report, resp_type='JSonResponse', req_id='0'):
    """Returns the Visualization API Data Table containing the number of 
    busy slaves at each moment (each int_size interval) over a timeframe, 
    based on the SlavesReport.

    Input: SlavesReport, resp_type
    Output: JSON/JSCode of resulting data table
    """
    # gviz table description (columns)
    description = {
        'datetime': ('datetime', 'Date'),
        'busy': ('number', '# Busy Slaves'),
    }

    # gviz table data (rows)
    data = []
    busy = report.get_int_busy()
    for inter in xrange(report.int_no):
        data.append({
            'datetime': datetime.fromtimestamp(
                report.get_interval_timestamp(inter)),
            'busy': busy[inter],
        })

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)

    if resp_type == 'JSCode':
        return data_table.ToJSCode("jscode_data",
            columns_order=('datetime', 'busy'))
    else:
        return data_table.ToJSonResponse(req_id=req_id, 
            columns_order=('datetime', 'busy'))

def csv_slaves_int_busy_silos(report):
    """Returns the percentage of busy slaves at each moment (each int_size 
    interval) within a silos, for all silos, over a timeframe. The Data Table 
    is based on the SlavesReport.

    Input: SlavesReport, resp_type
    Output: CSV formatted
    """
    int_busy, totals = report.get_int_busy_silos()
    total_slaves = report.total_slaves()

    data = ['Date,Totals,' + ','.join(report.silos)]
    for inter in xrange(report.int_no):
        row = [
            str(datetime.fromtimestamp(report.get_interval_timestamp(inter))),
            "%.2f" % (int_busy['Totals'][inter] * 100. / total_slaves 
                if total_slaves else 0,)
        ]
        for silos_name in report.silos:
            row.append("%.2f" % (int_busy[silos_name][inter] * 100. / 
                totals[silos_name] if totals[silos_name] else 0,))
        data.append(','.join(row))

    return '\n'.join(data)

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
