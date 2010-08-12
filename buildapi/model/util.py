import time

def get_time_interval(starttime, endtime):
    """Returns (sarttime2, endtime2) tuple, where the starttime2 is the exact 
    value of input parameter starttime if specified, or endtime minus 24 hours
    if not. endtime2 is the exact value of input parameter endtime if specified,
    or starttime plus 24 hours or current time (if starttime is not specified 
    either).

    Input: stattime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
    Output: (stattime2, endtime2)
    """
    nowtime = time.time()
    if not endtime:
        endtime = min(starttime+24*3600 if starttime else nowtime, nowtime)
    if not starttime:
        starttime = endtime-24*3600

    return starttime, endtime
