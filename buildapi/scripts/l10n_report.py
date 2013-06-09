#!/usr/bin/env python
try:
    import simplejson as json
    assert json
except ImportError:
    import json

import gzip


status_strings = {
    0: 'OK',
    1: 'WARNINGS',
    2: 'FAILURE',
    3: 'SKIPPED',
    4: 'EXCEPTION',
    5: 'RETRY',
}


def parse_builds_report(data, output, skip=(0, 5)):
    for build in data['builds']:
        # Ignore non-l10n builders
        # We look at the buildername property to tell
        props = build['properties']

        if 'buildername' not in props:
            # something went wrong adding the job to the db
            continue
        if 'l10n' not in props['buildername']:
            continue

	if 'platform' not in props:
            # something went wrong adding the job to the db
            continue
        if props['platform'] == 'android':
            # it's weird
            # TODO: handle later
            continue

        vals = props.copy()
        if build['result'] in skip:
            # No need to report on this since it worked
            continue

        try:
            output.write("%(branch)s %(platform)s %(locale)s\n" % vals)
            output.write("    %s\n" % status_strings[build['result']])
            output.write("    %s\n" % vals['log_url'])
            if 'packageUrl' not in vals:
                output.write("    no package url\n")
            else:
                output.write("    %s\n" % vals['packageUrl'])
        except KeyError, e:
            print e, build


def main():
    import sys
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-o", "--output", dest="output", help="file to write output to")

    options, args = parser.parse_args()

    if options.output:
        output = open(options.output, "w")
    else:
        output = sys.stdout

    for fn in args:
        data = json.load(gzip.open(fn))
        parse_builds_report(data, output)

if __name__ == '__main__':
    main()
