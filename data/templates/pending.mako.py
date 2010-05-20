# -*- encoding:utf-8 -*-
from mako import runtime, filters, cache
UNDEFINED = runtime.UNDEFINED
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 5
_modified_time = 1274397867.288044
_template_filename='/home/catlee/mozilla/buildapi/buildapi/templates/pending.mako'
_template_uri='/pending.mako'
_template_cache=cache.Cache(__name__, _modified_time)
_source_encoding='utf-8'
from webhelpers.html import escape
_exports = []


def render_body(context,**pageargs):
    context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)
        c = context.get('c', UNDEFINED)
        __M_writer = context.writer()
        # SOURCE LINE 1
        __M_writer(u'Here is the list of pending builds!</br>\n\n')
        # SOURCE LINE 3
        for b in c.pending_builds:
            # SOURCE LINE 4
            __M_writer(u'ID: ')
            __M_writer(escape(b['id']))
            __M_writer(u'<br/>\n')
            pass
        return ''
    finally:
        context.caller_stack._pop_frame()


