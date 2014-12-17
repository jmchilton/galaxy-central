import logging
import re
import traceback
import sys
import uuid
from math import isinf

from .interface import (
    ToolSource,
    PagesSource,
    PageSource,
    InputSource,
)
from galaxy.util import string_as_bool, xml_text, xml_to_string
from galaxy.tools.deps import requirements
import galaxy.tools
from galaxy.tools.parameters import output_collect
from galaxy.tools.parameters import dynamic_options

log = logging.getLogger( __name__ )


class XmlToolSource(ToolSource):
    """ Responsible for parsing a tool from classic Galaxy representation.
    """

    def __init__(self, root):
        self.root = root

    def parse_version(self):
        return self.root.get("version", None)

    def parse_id(self):
        return self.root.get("id")

    def parse_tool_module(self):
        root = self.root
        if root.find( "type" ) is not None:
            type_elem = root.find( "type" )
            module = type_elem.get( 'module', 'galaxy.tools' )
            cls = type_elem.get( 'class' )
            return module, cls

        return None

    def parse_action_module(self):
        root = self.root
        action_elem = root.find( "action" )
        if action_elem is not None:
            module = action_elem.get( 'module' )
            cls = action_elem.get( 'class' )
            return module, cls
        else:
            return None

    def parse_tool_type(self):
        root = self.root
        if root.get( 'tool_type', None ) is not None:
            return root.get( 'tool_type' )

    def parse_name(self):
        return self.root.get( "name" )

    def parse_description(self):
        return xml_text(self.root, "description")

    def parse_is_multi_byte(self):
        return self._get_attribute_as_bool( "is_multi_byte", self.default_is_multi_byte )

    def parse_display_interface(self, default):
        return self._get_attribute_as_bool( "display_interface", default )

    def parse_require_login(self, default):
        return self._get_attribute_as_bool( "require_login", default )

    def parse_request_param_translation_elem(self):
        return self.root.find( "request_param_translation" )

    def parse_command(self):
        command_el = self._command_el
        return (command_el is not None) and command_el.text

    def parse_interpreter(self):
        command_el = self._command_el
        return (command_el is not None) and command_el.get("interpreter", None)

    def parse_version_command(self):
        version_cmd = self.root.find("version_command")
        if version_cmd is not None:
            return version_cmd.text
        else:
            return None

    def parse_version_command_interpreter(self):
        if self.parse_version_command() is not None:
            version_cmd = self.root.find("version_command")
            version_cmd_interpreter = version_cmd.get( "interpreter", None )
            if version_cmd_interpreter:
                return version_cmd_interpreter
        return None

    def parse_parallelism(self):
        parallelism = self.root.find("parallelism")
        parallelism_info = None
        if parallelism is not None and parallelism.get("method"):
            from galaxy.jobs import ParallelismInfo
            return ParallelismInfo(parallelism)
        return parallelism_info

    def parse_hidden(self):
        hidden = xml_text(self.root, "hidden")
        if hidden:
            hidden = string_as_bool(hidden)
        return hidden

    def parse_redirect_url_params_elem(self):
        return self.root.find("redirect_url_params")

    @property
    def _command_el(self):
        return self.root.find("command")

    def _get_attribute_as_bool( self, attribute, default, elem=None ):
        if elem is None:
            elem = self.root
        return string_as_bool( elem.get( attribute, default ) )

    def parse_requirements_and_containers(self):
        return requirements.parse_requirements_from_xml(self.root)

    def parse_input_pages(self):
        return XmlPagesSource(self.root)

    def parse_outputs(self, tool):
        out_elem = self.root.find("outputs")
        if out_elem is None:
            return []

        def _parse(data_elem):
            return self._parse_output(data_elem, tool)

        return map(_parse, out_elem.findall("data"))

    def _parse_output(self, data_elem, tool):
        output = galaxy.tools.ToolOutput( data_elem.get("name") )
        output.format = data_elem.get("format", "data")
        output.change_format = data_elem.findall("change_format")
        output.format_source = data_elem.get("format_source", None)
        output.metadata_source = data_elem.get("metadata_source", "")
        output.parent = data_elem.get("parent", None)
        output.label = xml_text( data_elem, "label" )
        output.count = int( data_elem.get("count", 1) )
        output.filters = data_elem.findall( 'filter' )
        output.tool = tool
        output.from_work_dir = data_elem.get("from_work_dir", None)
        output.hidden = string_as_bool( data_elem.get("hidden", "") )
        output.actions = galaxy.tools.ToolOutputActionGroup( output, data_elem.find( 'actions' ) )
        output.dataset_collectors = output_collect.dataset_collectors_from_elem( data_elem )
        return output

    def parse_stdio(self):
        parser = StdioParser(self.root)
        return parser.stdio_exit_codes, parser.stdio_regexes

    def parse_help(self):
        help_elem = self.root.find( 'help' )
        return help_elem.text if help_elem is not None else None

    def parse_tests_to_dict(self):
        tests_elem = self.root.find("tests")
        tests = []
        rval = dict(
            tests=tests
        )

        if tests_elem is not None:
            for i, test_elem in enumerate(tests_elem.findall("test")):
                tests.append(_test_elem_to_dict(test_elem, i))

            _copy_to_dict_if_present(tests_elem, rval, ["interactor"])

        return rval


def _test_elem_to_dict(test_elem, i):
    rval = dict(
        outputs=__parse_output_elems(test_elem),
        inputs=__parse_input_elems(test_elem, i),
        command=__parse_assert_list_from_elem( test_elem.find("assert_command") ),
        stdout=__parse_assert_list_from_elem( test_elem.find("assert_stdout") ),
        stderr=__parse_assert_list_from_elem( test_elem.find("assert_stderr") ),
        expect_exit_code=test_elem.get("expect_exit_code"),
        expect_failure=string_as_bool(test_elem.get("expect_failure", False)),
    )
    _copy_to_dict_if_present(test_elem, rval, ["interactor", "num_outputs"])
    return rval


def __parse_input_elems(test_elem, i):
    __expand_input_elems( test_elem )
    return __parse_inputs_elems( test_elem, i )


def __parse_output_elems( test_elem ):
    outputs = []
    for output_elem in test_elem.findall( "output" ):
        name, file, attributes = __parse_output_elem( output_elem )
        outputs.append( ( name, file, attributes ) )
    return outputs


def __parse_output_elem( output_elem ):
    attrib = dict( output_elem.attrib )
    name = attrib.pop( 'name', None )
    if name is None:
        raise Exception( "Test output does not have a 'name'" )

    file, attributes = __parse_test_attributes( output_elem, attrib )
    primary_datasets = {}
    for primary_elem in ( output_elem.findall( "discovered_dataset" ) or [] ):
        primary_attrib = dict( primary_elem.attrib )
        designation = primary_attrib.pop( 'designation', None )
        if designation is None:
            raise Exception( "Test primary dataset does not have a 'designation'" )
        primary_datasets[ designation ] = __parse_test_attributes( primary_elem, primary_attrib )
    attributes[ "primary_datasets" ] = primary_datasets
    return name, file, attributes


def __parse_command_elem( test_elem ):
    assert_elem = test_elem.find("command")
    return __parse_assert_list_from_elem( assert_elem )


def __parse_test_attributes( output_elem, attrib ):
    assert_list = __parse_assert_list( output_elem )
    file = attrib.pop( 'file', None )
    # File no longer required if an list of assertions was present.
    attributes = {}
    # Method of comparison
    attributes['compare'] = attrib.pop( 'compare', 'diff' ).lower()
    # Number of lines to allow to vary in logs (for dates, etc)
    attributes['lines_diff'] = int( attrib.pop( 'lines_diff', '0' ) )
    # Allow a file size to vary if sim_size compare
    attributes['delta'] = int( attrib.pop( 'delta', '10000' ) )
    attributes['sort'] = string_as_bool( attrib.pop( 'sort', False ) )
    extra_files = []
    if 'ftype' in attrib:
        attributes['ftype'] = attrib['ftype']
    for extra in output_elem.findall( 'extra_files' ):
        extra_files.append( __parse_extra_files_elem( extra ) )
    metadata = {}
    for metadata_elem in output_elem.findall( 'metadata' ):
        metadata[ metadata_elem.get('name') ] = metadata_elem.get( 'value' )
    if not (assert_list or file or extra_files or metadata):
        raise Exception( "Test output defines nothing to check (e.g. must have a 'file' check against, assertions to check, etc...)")
    attributes['assert_list'] = assert_list
    attributes['extra_files'] = extra_files
    attributes['metadata'] = metadata
    return file, attributes


def __parse_assert_list( output_elem ):
    assert_elem = output_elem.find("assert_contents")
    return __parse_assert_list_from_elem( assert_elem )


def __parse_assert_list_from_elem( assert_elem ):
    assert_list = None

    def convert_elem(elem):
        """ Converts and XML element to a dictionary format, used by assertion checking code. """
        tag = elem.tag
        attributes = dict( elem.attrib )
        child_elems = list( elem.getchildren() )
        converted_children = []
        for child_elem in child_elems:
            converted_children.append( convert_elem(child_elem) )
        return {"tag": tag, "attributes": attributes, "children": converted_children}
    if assert_elem is not None:
        assert_list = []
        for assert_child in list(assert_elem):
            assert_list.append(convert_elem(assert_child))

    return assert_list


def __parse_extra_files_elem( extra ):
    # File or directory, when directory, compare basename
    # by basename
    extra_type = extra.get( 'type', 'file' )
    extra_name = extra.get( 'name', None )
    assert extra_type == 'directory' or extra_name is not None, \
        'extra_files type (%s) requires a name attribute' % extra_type
    extra_value = extra.get( 'value', None )
    assert extra_value is not None, 'extra_files requires a value attribute'
    extra_attributes = {}
    extra_attributes['compare'] = extra.get( 'compare', 'diff' ).lower()
    extra_attributes['delta'] = extra.get( 'delta', '0' )
    extra_attributes['lines_diff'] = int( extra.get( 'lines_diff', '0' ) )
    extra_attributes['sort'] = string_as_bool( extra.get( 'sort', False ) )
    return extra_type, extra_value, extra_name, extra_attributes


def __expand_input_elems( root_elem, prefix="" ):
    __append_prefix_to_params( root_elem, prefix )

    repeat_elems = root_elem.findall( 'repeat' )
    indices = {}
    for repeat_elem in repeat_elems:
        name = repeat_elem.get( "name" )
        if name not in indices:
            indices[ name ] = 0
            index = 0
        else:
            index = indices[ name ] + 1
            indices[ name ] = index

        new_prefix = __prefix_join( prefix, name, index=index )
        __expand_input_elems( repeat_elem, new_prefix )
        __pull_up_params( root_elem, repeat_elem )
        root_elem.remove( repeat_elem )

    cond_elems = root_elem.findall( 'conditional' )
    for cond_elem in cond_elems:
        new_prefix = __prefix_join( prefix, cond_elem.get( "name" ) )
        __expand_input_elems( cond_elem, new_prefix )
        __pull_up_params( root_elem, cond_elem )
        root_elem.remove( cond_elem )


def __append_prefix_to_params( elem, prefix ):
    for param_elem in elem.findall( 'param' ):
        param_elem.set( "name", __prefix_join( prefix, param_elem.get( "name" ) ) )


def __pull_up_params( parent_elem, child_elem ):
    for param_elem in child_elem.findall( 'param' ):
        parent_elem.append( param_elem )
        child_elem.remove( param_elem )


def __prefix_join( prefix, name, index=None ):
    name = name if index is None else "%s_%d" % ( name, index )
    return name if not prefix else "%s|%s" % ( prefix, name )


def _copy_to_dict_if_present( elem, rval, attributes ):
    for attribute in attributes:
        if attribute in elem.attrib:
            rval[attribute] = elem.get(attribute)
    return rval


def __parse_inputs_elems( test_elem, i ):
    raw_inputs = []
    for param_elem in test_elem.findall( "param" ):
        name, value, attrib = __parse_param_elem( param_elem, i )
        raw_inputs.append( ( name, value, attrib ) )
    return raw_inputs


def __parse_param_elem( param_elem, i=0 ):
    attrib = dict( param_elem.attrib )
    if 'values' in attrib:
        value = attrib[ 'values' ].split( ',' )
    elif 'value' in attrib:
        value = attrib['value']
    else:
        value = None
    attrib['children'] = list( param_elem.getchildren() )
    if attrib['children']:
        # At this time, we can assume having children only
        # occurs on DataToolParameter test items but this could
        # change and would cause the below parsing to change
        # based upon differences in children items
        attrib['metadata'] = []
        attrib['composite_data'] = []
        attrib['edit_attributes'] = []
        # Composite datasets need to be renamed uniquely
        composite_data_name = None
        for child in attrib['children']:
            if child.tag == 'composite_data':
                attrib['composite_data'].append( child )
                if composite_data_name is None:
                    # Generate a unique name; each test uses a
                    # fresh history.
                    composite_data_name = '_COMPOSITE_RENAMED_t%d_%s' \
                        % ( i, uuid.uuid1().hex )
            elif child.tag == 'metadata':
                attrib['metadata'].append( child )
            elif child.tag == 'metadata':
                attrib['metadata'].append( child )
            elif child.tag == 'edit_attributes':
                attrib['edit_attributes'].append( child )
            elif child.tag == 'collection':
                attrib[ 'collection' ] = galaxy.tools.TestCollectionDef( child, __parse_param_elem )
        if composite_data_name:
            # Composite datasets need implicit renaming;
            # inserted at front of list so explicit declarations
            # take precedence
            attrib['edit_attributes'].insert( 0, { 'type': 'name', 'value': composite_data_name } )
    name = attrib.pop( 'name' )
    return ( name, value, attrib )


class StdioParser(object):

    def __init__(self, root):
        try:
            self.stdio_exit_codes = list()
            self.stdio_regexes = list()

            # We should have a single <stdio> element, but handle the case for
            # multiples.
            # For every stdio element, add all of the exit_code and regex
            # subelements that we find:
            for stdio_elem in ( root.findall( 'stdio' ) ):
                self.parse_stdio_exit_codes( stdio_elem )
                self.parse_stdio_regexes( stdio_elem )
        except Exception:
            log.error( "Exception in parse_stdio! " + str(sys.exc_info()) )

    def parse_stdio_exit_codes( self, stdio_elem ):
        """
        Parse the tool's <stdio> element's <exit_code> subelements.
        This will add all of those elements, if any, to self.stdio_exit_codes.
        """
        try:
            # Look for all <exit_code> elements. Each exit_code element must
            # have a range/value.
            # Exit-code ranges have precedence over a single exit code.
            # So if there are value and range attributes, we use the range
            # attribute. If there is neither a range nor a value, then print
            # a warning and skip to the next.
            for exit_code_elem in ( stdio_elem.findall( "exit_code" ) ):
                exit_code = galaxy.tools.ToolStdioExitCode()
                # Each exit code has an optional description that can be
                # part of the "desc" or "description" attributes:
                exit_code.desc = exit_code_elem.get( "desc" )
                if None == exit_code.desc:
                    exit_code.desc = exit_code_elem.get( "description" )
                # Parse the error level:
                exit_code.error_level = (
                    self.parse_error_level( exit_code_elem.get( "level" )))
                code_range = exit_code_elem.get( "range", "" )
                if None == code_range:
                    code_range = exit_code_elem.get( "value", "" )
                if None == code_range:
                    log.warning( "Tool stdio exit codes must have "
                                 + "a range or value" )
                    continue
                # Parse the range. We look for:
                #   :Y
                #  X:
                #  X:Y   - Split on the colon. We do not allow a colon
                #          without a beginning or end, though we could.
                # Also note that whitespace is eliminated.
                # TODO: Turn this into a single match - it should be
                # more efficient.
                code_range = re.sub( "\s", "", code_range )
                code_ranges = re.split( ":", code_range )
                if ( len( code_ranges ) == 2 ):
                    if ( None == code_ranges[0] or '' == code_ranges[0] ):
                        exit_code.range_start = float( "-inf" )
                    else:
                        exit_code.range_start = int( code_ranges[0] )
                    if ( None == code_ranges[1] or '' == code_ranges[1] ):
                        exit_code.range_end = float( "inf" )
                    else:
                        exit_code.range_end = int( code_ranges[1] )
                # If we got more than one colon, then ignore the exit code.
                elif ( len( code_ranges ) > 2 ):
                    log.warning( "Invalid tool exit_code range %s - ignored"
                                 % code_range )
                    continue
                # Else we have a singular value. If it's not an integer, then
                # we'll just write a log message and skip this exit_code.
                else:
                    try:
                        exit_code.range_start = int( code_range )
                    except:
                        log.error( code_range )
                        log.warning( "Invalid range start for tool's exit_code %s: exit_code ignored" % code_range )
                        continue
                    exit_code.range_end = exit_code.range_start
                # TODO: Check if we got ">", ">=", "<", or "<=":
                # Check that the range, regardless of how we got it,
                # isn't bogus. If we have two infinite values, then
                # the start must be -inf and the end must be +inf.
                # So at least warn about this situation:
                if ( isinf( exit_code.range_start ) and
                     isinf( exit_code.range_end ) ):
                    log.warning( "Tool exit_code range %s will match on "
                                 + "all exit codes" % code_range )
                self.stdio_exit_codes.append( exit_code )
        except Exception:
            log.error( "Exception in parse_stdio_exit_codes! "
                       + str(sys.exc_info()) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg )

    def parse_stdio_regexes( self, stdio_elem ):
        """
        Look in the tool's <stdio> elem for all <regex> subelements
        that define how to look for warnings and fatal errors in
        stdout and stderr. This will add all such regex elements
        to the Tols's stdio_regexes list.
        """
        try:
            # Look for every <regex> subelement. The regular expression
            # will have "match" and "source" (or "src") attributes.
            for regex_elem in ( stdio_elem.findall( "regex" ) ):
                # TODO: Fill in ToolStdioRegex
                regex = galaxy.tools.ToolStdioRegex()
                # Each regex has an optional description that can be
                # part of the "desc" or "description" attributes:
                regex.desc = regex_elem.get( "desc" )
                if None == regex.desc:
                    regex.desc = regex_elem.get( "description" )
                # Parse the error level
                regex.error_level = (
                    self.parse_error_level( regex_elem.get( "level" ) ) )
                regex.match = regex_elem.get( "match", "" )
                if None == regex.match:
                    # TODO: Convert the offending XML element to a string
                    log.warning( "Ignoring tool's stdio regex element %s - "
                                 "the 'match' attribute must exist" )
                    continue
                # Parse the output sources. We look for the "src", "source",
                # and "sources" attributes, in that order. If there is no
                # such source, then the source defaults to stderr & stdout.
                # Look for a comma and then look for "err", "error", "out",
                # and "output":
                output_srcs = regex_elem.get( "src" )
                if None == output_srcs:
                    output_srcs = regex_elem.get( "source" )
                if None == output_srcs:
                    output_srcs = regex_elem.get( "sources" )
                if None == output_srcs:
                    output_srcs = "output,error"
                output_srcs = re.sub( "\s", "", output_srcs )
                src_list = re.split( ",", output_srcs )
                # Just put together anything to do with "out", including
                # "stdout", "output", etc. Repeat for "stderr", "error",
                # and anything to do with "err". If neither stdout nor
                # stderr were specified, then raise a warning and scan both.
                for src in src_list:
                    if re.search( "both", src, re.IGNORECASE ):
                        regex.stdout_match = True
                        regex.stderr_match = True
                    if re.search( "out", src, re.IGNORECASE ):
                        regex.stdout_match = True
                    if re.search( "err", src, re.IGNORECASE ):
                        regex.stderr_match = True
                    if (not regex.stdout_match and not regex.stderr_match):
                        log.warning( "Tool id %s: unable to determine if tool "
                                     "stream source scanning is output, error, "
                                     "or both. Defaulting to use both." % self.id )
                        regex.stdout_match = True
                        regex.stderr_match = True
                self.stdio_regexes.append( regex )
        except Exception:
            log.error( "Exception in parse_stdio_exit_codes! "
                       + str(sys.exc_info()) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg )

    # TODO: This method doesn't have to be part of the Tool class.
    def parse_error_level( self, err_level ):
        """
        Parses error level and returns error level enumeration. If
        unparsable, returns 'fatal'
        """
        from galaxy.jobs.error_level import StdioErrorLevel
        return_level = StdioErrorLevel.FATAL
        try:
            if err_level:
                if ( re.search( "log", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.LOG
                elif ( re.search( "warning", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.WARNING
                elif ( re.search( "fatal", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.FATAL
                else:
                    log.debug( "Tool %s: error level %s did not match log/warning/fatal" %
                               ( self.id, err_level ) )
        except Exception:
            log.error( "Exception in parse_error_level "
                       + str(sys.exc_info() ) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg )
        return return_level


class XmlPagesSource(PagesSource):

    def __init__(self, root):
        self.input_elem = root.find("inputs")
        page_sources = []
        if self.input_elem:
            pages_elem = self.input_elem.findall( "page" )
            for page in ( pages_elem or [ self.input_elem ] ):
                page_sources.append(XmlPageSource(page))
        super(XmlPagesSource, self).__init__(page_sources)

    @property
    def inputs_defined(self):
        return self.input_elem is not None


class XmlPageSource(PageSource):

    def __init__(self, parent_elem):
        self.parent_elem = parent_elem

    def parse_display(self):
        display_elem = self.parent_elem.find("display")
        if display_elem is not None:
            display = xml_to_string(display_elem)
        else:
            display = None
        return display

    def parse_input_sources(self):
        return map(XmlInputSource, self.parent_elem)


class XmlInputSource(InputSource):

    def __init__(self, input_elem):
        self.input_elem = input_elem
        self.input_type = self.input_elem.tag

    def parse_input_type(self):
        return self.input_type

    def elem(self):
        return self.input_elem

    def get(self, key, value=None):
        return self.input_elem.get(key, value)

    def get_bool(self, key, default):
        return string_as_bool( self.get(key, default ) )

    def parse_label(self):
        return xml_text(self.input_elem, "label")

    def parse_help(self):
        return xml_text(self.input_elem, "help")

    def parse_sanitizer_elem(self):
        return self.input_elem.find("sanitizer")

    def parse_validator_elems(self):
        return self.input_elem.findall("validator")

    def parse_dynamic_options(self, param):
        """ Return a galaxy.tools.parameters.dynamic_options.DynamicOptions
        if appropriate.
        """
        options_elem = self.input_elem.find( 'options' )
        if options_elem is None:
            options = None
        else:
            options = dynamic_options.DynamicOptions( options_elem, param )
        return options

    def parse_static_options(self):
        static_options = list()
        elem = self.input_elem
        for index, option in enumerate( elem.findall( "option" ) ):
            value = option.get( "value" )
            selected = string_as_bool( option.get( "selected", False ) )
            static_options.append( ( option.text or value, value, selected ) )
        return static_options

    def parse_optional(self, default=None):
        """ Return boolean indicating wheter parameter is optional. """
        elem = self.input_elem
        if self.get('type') == "data_column":
            # Allow specifing force_select for backward compat., but probably
            # should use optional going forward for consistency with other
            # parameters.
            if "force_select" in elem.attrib:
                force_select = string_as_bool( elem.get( "force_select" ) )
            else:
                force_select = not string_as_bool( elem.get( "optional", False ) )
            return not force_select

        if default is None:
            default = self.default_optional
        return self.get_bool( "optional", default )

    def parse_conversion_tuples(self):
        elem = self.input_elem
        conversions = []
        for conv_elem in elem.findall( "conversion" ):
            name = conv_elem.get( "name" )  # name for commandline substitution
            conv_extensions = conv_elem.get( "type" )  # target datatype extension
            conversions.append((name, conv_extensions))
        return conversions

    def parse_nested_inputs_source(self):
        elem = self.input_elem
        return XmlPageSource(elem)

    def parse_test_input_source(self):
        elem = self.input_elem
        input_elem = elem.find( "param" )
        assert input_elem is not None, "<conditional> must have a child <param>"
        return XmlInputSource(input_elem)

    def parse_when_input_sources(self):
        elem = self.input_elem

        sources = []
        for case_elem in elem.findall( "when" ):
            value = case_elem.get( "value" )
            case_page_source = XmlPageSource(case_elem)
            sources.append((value, case_page_source))
        return sources
