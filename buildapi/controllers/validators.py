from formencode import Schema
from formencode.validators import FancyValidator, Int, Number, String, \
Invalid, OneOf, Bool

from buildapi.model.util import BUILDPOOL_MASTERS, SOURCESTAMPS_BRANCH, \
PLATFORMS_BUILDERNAME, BUILD_TYPE_BUILDERNAME, JOB_TYPE_BUILDERNAME, \
BUILDERS_DETAIL_LEVELS
from buildapi.model.util import get_time_interval

class FormatValidator(OneOf, String):
    """format parameter validator."""
    list = ('html', 'json', 'chart')
    if_empty = 'html'
    if_missing = 'html'

class UnixtimestampValidator(Number):
    """Unixtimestamp validator, used for starttime and endtime parameters."""
    if_empty = None
    if_missing = None

class IntervalValidator(Int):
    """Time inverval validator. 

    The interval is speficied in seconds, with the default at 2 hours (7200s).
    """
    if_empty = 0
    if_missing = 0
    min=0

class PoolValidator(OneOf, String):
    """Pool validator. Must be one of BUILDPOOL_MASTERS keys."""
    list = BUILDPOOL_MASTERS.keys()
    if_empty = 'buildpool'
    if_missing = 'buildpool'

class BranchNameValidator(OneOf, String):
    """Branch name validator. Must be one of SOURCESTAMPS_BRANCH keys."""
    list = SOURCESTAMPS_BRANCH.keys()
    if_empty = 'mozilla-central'
    if_missing = 'mozilla-central'

class SeparatorOneOfValidator(OneOf):
    """Exactly like OneOf validator, with 'testValueList' set to True, 
    checks if the list of parameters is a subset of the allowed values 
    ('list' parameter), except the input is not a list, but a string of 
    multiple values seprated by the spefied 'separator'.
    """
    testValueList = True
    separator = ','
    list = []
    if_empty = []
    if_missing = []

    def _to_python(self, value, state):
        values_list = value.split(self.separator)
        return values_list

class BranchListValidator(SeparatorOneOfValidator):
    """Multi value branch validator. 

    Parameters must be a subset of SOURCESTAMPS_BRANCH keys.
    """
    list = SOURCESTAMPS_BRANCH.keys()

class PlatformValidator(SeparatorOneOfValidator):
    """Multi value platform validator. 

    Parameters must be a subset of PLATFORMS_BUILDERNAME keys.
    """
    list = PLATFORMS_BUILDERNAME.keys()

class BuildTypeValidator(SeparatorOneOfValidator):
    """Multi value build type validator. 

    Parameters must be a subset of BUILD_TYPE_BUILDERNAME keys.
    """
    list = BUILD_TYPE_BUILDERNAME.keys()

class JobTypeValidator(SeparatorOneOfValidator):
    """Multi value job type validator. 

    Parameters must be a subset of JOB_TYPE_BUILDERNAME keys.
    """
    list = JOB_TYPE_BUILDERNAME.keys()

class DetailLevelValidator(OneOf, String):
    """Detail level validator. 

    Parameter must be one of BUILDERS_DETAIL_LEVELS.
    """
    list = BUILDERS_DETAIL_LEVELS
    if_empty = 'builder'
    if_missing = 'builder'

class NumberTypeValidator(OneOf, String):
    """Number Type Validator. 
    
    Parameter must be either a full number, or a percentage of the global sum.
    """
    list = ('full', 'ptg')  # full number or percentage
    if_empty = 'full'
    if_missing = 'full'

class RequestIdValidator(FancyValidator):
    """Intended as a chained validator to be called after validating all 
    parameters in the schema.

    It parses 'reqId' value out of 'tqx' parameter, meaningful only if format 
    equals 'chart'.
    """
    def to_python(self, value_dict, state):
        value_dict['reqid'] = self._parse_reqid(value_dict.get('tqx', ''))
        return value_dict

    def _parse_reqid(self, tqx):
        req_id = '0'
        if tqx:
            for param in tqx.split(';'):
                if (param.find(':') > 0):
                    (par_key, par_value) = param.split(':')
                    if (par_key == 'reqId'):
                        req_id = par_value

        return req_id

class DateCompare(FancyValidator):
    """Validates that starttime is before endtime."""
    messages = dict(invalid="statttime must be before endtime")

    def validate_python(self, value_dict, state):
        starttime = value_dict.get('starttime', None)
        endtime = value_dict.get('endtime', None)

        if starttime and endtime and starttime > endtime:
            msg = self.message('invalid', state)

            raise Invalid(msg, value_dict, state,
                error_dict=dict(starttime=msg))

class DateInit(FancyValidator):
    """Initializes starttime and entime if not specified."""

    def to_python(self, value_dict, state):
        starttime, endtime = value_dict['starttime'], value_dict['endtime']
        starttime, endtime = get_time_interval(starttime, endtime)

        value_dict['starttime'] = starttime
        value_dict['endtime'] = endtime

        return value_dict

class IntSizeInit(FancyValidator):
    """Initializes int_size proportionally to selected time interval 
    (starttime, endtime) into specified number of divisions."""
    divisions = 12

    def to_python(self, value_dict, state):
        starttime = value_dict['starttime']
        endtime = value_dict['endtime']
        int_size = value_dict['int_size']

        if not int_size:
            value_dict['int_size'] = int(
                (endtime - starttime) // self.divisions)

        return value_dict

class ReportSchema(Schema):
    """Base report schema."""
    allow_extra_fields = True
    filter_extra_fields = True
    format = FormatValidator(list=('html', 'json', 'chart'))
    tqx = String(if_missing='', if_empty='')
    starttime = UnixtimestampValidator()
    endtime = UnixtimestampValidator()

    chained_validators = [DateCompare(), DateInit(), RequestIdValidator()]

class PushesSchema(ReportSchema):
    """Pushes Report Schema."""
    int_size = IntervalValidator()
    branches = BranchListValidator()
    type = OneOf(list=['int', 'hourly', 'all'], if_empty='all', 
        if_missing='all')

    chained_validators = ReportSchema.chained_validators + [ IntSizeInit() ]

class WaittimesSchema(ReportSchema):
    """Wait Times Report Schema."""
    int_size = IntervalValidator()
    pool = PoolValidator()
    num = NumberTypeValidator()
    mpb = Int(min=0, if_missing=15, if_empty=15)    # minutes per block
    maxb = Int(min=0, if_missing=1000, if_empty=1000) # max block

    chained_validators = ReportSchema.chained_validators + [ IntSizeInit() ]

class EndtoendSchema(ReportSchema):
    """End to End Times Report Schema."""
    branch_name = BranchNameValidator()

class EndtoendRevisionSchema(ReportSchema):
    """Revision Report Schema."""
    format = FormatValidator(list=('html', 'json'))
    starttime = None    # no starttime and endtime parameters
    endtime = None
    branch_name = BranchNameValidator()
    revision = String(min=12)

    chained_validators = [RequestIdValidator()]

class BuildersSchema(ReportSchema):
    """Average Time per Builder Report Schema."""
    branch_name = BranchNameValidator()
    platform = PlatformValidator()
    build_type = BuildTypeValidator()
    job_type = JobTypeValidator()
    detail_level = DetailLevelValidator()

class BuilderDetailsSchema(ReportSchema):
    """Builder Report Schema."""
    format = FormatValidator(list=('html', 'json'))
    buildername = String(not_empty=True)

class IdleJobsSchema(ReportSchema):
    """IdleJobs Report Schema"""
    int_size = IntervalValidator()

class TestRunSchema(ReportSchema):
    """Test Run Report Schema"""
    btype    = String(if_missing=None, if_empty=None)
    platform = String(if_missing=None, if_empty=None)
    category = String(if_missing=None, if_empty=None)
    group    = Bool(if_missing=None)
