from unittest import TestCase

from galaxy.tools.parameters import basic
from galaxy.util import bunch
from elementtree.ElementTree import XML

import tools_support


class BaseParameterTestCase( TestCase, tools_support.UsesApp ):

    def setUp(self):
        self.setup_app( mock_model=False )
        self.mock_tool = bunch.Bunch(
            app=self.app,
            tool_type="default",
        )

    def _parameter_for(self, **kwds):
        content = kwds["xml"]
        param_xml = XML( content )
        return basic.ToolParameter.build( self.mock_tool, param_xml )


class ParameterParsingTestCase( BaseParameterTestCase ):
    """ Test the parsing of XML for most parameter types - in many
    ways these are not very good tests since they break the abstraction
    established by the tools. The docs tests in basic.py are better but
    largely rely on HTML stuff we are moving to the client side so they
    those tests may need to be updated anyway.

    It occurs to me that rewriting this stuff to test to_dict would
    be much better - since that is a public API of the the tools.
    """

    def test_parse_help_and_label(self):
        param = self._parameter_for(xml="""
            <param type="text" name="texti" size="8" value="mydefault" label="x" help="y" />
        """)
        assert param.label == "x"
        assert param.help == "y"

        param = self._parameter_for(xml="""
            <param type="text" name="texti" size="8" value="mydefault">
                <label>x2</label>
                <help>y2</help>
            </param>
        """)
        assert param.label == "x2"
        assert param.help == "y2"

    def test_parse_sanitizers(self):
        param = self._parameter_for(xml="""
            <param type="text" name="texti" size="8" value="mydefault">
              <sanitizer invalid_char="">
                <valid initial="string.digits"><add value=","/> </valid>
              </sanitizer>
            </param>
        """)
        sanitizer = param.sanitizer
        assert sanitizer is not None
        assert sanitizer.sanitize_param("a") == ""
        assert sanitizer.sanitize_param(",") == ","

    def test_parse_optional(self):
        param = self._parameter_for(xml="""
            <param type="text" name="texti" size="8" value="mydefault" />
        """)
        assert param.optional is False

        param = self._parameter_for(xml="""
            <param type="text" name="texti" size="8" value="mydefault" optional="true" />
        """)
        assert param.optional is True

    def test_parse_validators(self):
        param = self._parameter_for(xml="""
            <param type="text" name="texti" size="8" value="mydefault">
                <validator type="unspecified_build" message="no genome?" />
            </param>
        """)
        assert param.validators[0].message == "no genome?"

    def test_text_params(self):
        param = self._parameter_for(xml="""
            <param type="text" name="texti" size="8" value="mydefault" />
        """)
        assert param.size == "8"
        assert param.value == "mydefault"
        assert param.type == "text"
        assert not param.area

    def test_text_area_params(self):
        param = self._parameter_for(xml="""
            <param type="text" name="textarea" area="true" />
        """)
        assert param.size is None
        assert param.value is None
        assert param.type == "text"
        assert param.area

    def test_integer_params(self):
        param = self._parameter_for(xml="""
            <param type="integer" name="intp" min="8" max="9" value="9" />
        """)
        assert param.name == "intp"
        assert param.value == "9"
        assert param.type == "integer"
        param.validate( 8 )
        self.assertRaises(Exception, lambda: param.validate( 10 ))

    def test_float_params(self):
        param = self._parameter_for(xml="""
            <param type="float" name="floatp" min="7.8" max="9.5" value="9" />
        """)
        assert param.name == "floatp"
        assert param.value == "9"
        assert param.type == "float"
        param.validate( 8.1 )
        self.assertRaises(Exception, lambda: param.validate( 10.0 ))

    def test_boolean_params(self):
        param = self._parameter_for(xml="""
            <param type="boolean" name="boolp" />
        """)
        assert param.name == "boolp"
        assert param.truevalue == "true"
        assert param.falsevalue == "false"
        assert param.type == "boolean"

        param = self._parameter_for(xml="""
            <param type="boolean" name="boolp" truevalue="t" falsevalue="f" />
        """)
        assert param.truevalue == "t"
        assert param.falsevalue == "f"

    def test_file_params(self):
        param = self._parameter_for(xml="""
            <param type="file" name="filep" ajax-upload="true" />
        """)
        assert param.name == "filep"
        assert param.type == "file"
        assert param.ajax

    def test_ftpfile_params(self):
        param = self._parameter_for(xml="""
            <param type="ftpfile" name="ftpfilep" />
        """)
        assert param.name == "ftpfilep"
        assert param.type == "ftpfile"

    def test_hidden(self):
        param = self._parameter_for(xml="""
            <param name="hiddenp" type="hidden" value="a hidden value" />
        """)
        assert param.name == "hiddenp"
        assert param.type == "hidden"
        assert param.value == "a hidden value"

    def test_base_url(self):
        param = self._parameter_for(xml="""
            <param name="urlp" type="baseurl" value="http://twitter.com/" />
        """)
        assert param.name == "urlp"
        assert param.type == "baseurl"
        assert param.value == "http://twitter.com/"

        param = self._parameter_for(xml="""
            <param name="urlp" type="baseurl" />
        """)
        assert param.value == ""

    def test_select_static(self):
        param = self._parameter_for(xml="""
            <param name="selectp" type="select" multiple="true">
                <option value="a">A</option>
                <option value="b" selected="true">B</option>
            </param>
        """)
        assert param.display is None
        assert param.multiple is True
        assert param.name == "selectp"
        assert param.type == "select"
        assert param.separator == ","

        assert param.options is None
        assert param.dynamic_options is None
        assert not param.is_dynamic

        options = param.static_options
        assert options[0][0] == "A"
        assert options[0][1] == "a"
        assert not options[0][2]

        assert options[1][0] == "B"
        assert options[1][1] == "b"
        assert options[1][2]

    def test_select_dynamic(self):
        param = self._parameter_for(xml="""
            <param name="selectp" type="select" dynamic_options="cow" display="checkboxes" separator="moo">
            </param>
        """)
        assert param.multiple is False
        assert param.options is None
        assert param.dynamic_options == "cow"
        ## This should be None or something - not undefined.
        # assert not param.static_options
        assert param.is_dynamic

        assert param.display == "checkboxes"
        assert param.separator == "moo"

    def test_select_options_from(self):
        param = self._parameter_for(xml="""
            <param name="selectp" type="select">
                <options from_data_table="cow">
                </options>
            </param>
        """)
        assert param.dynamic_options is None
        assert param.is_dynamic

        # More detailed tests of dynamic options should be placed
        # in test_select_parameters.
        assert param.options.missing_tool_data_table_name == "cow"

    def test_genome_build(self):
        param = self._parameter_for(xml="""
            <param name="genomep" type="genomebuild">
            </param>
        """)
        assert param.type == "genomebuild"
        assert param.name == "genomep"
        assert param.static_options

    def test_column_params(self):
        param = self._parameter_for(xml="""
            <param name="col1" type="data_column" data_ref="input1">
            </param>
        """)
        assert param.data_ref == "input1"
        assert param.usecolnames is False
        assert param.force_select is True
        assert param.numerical is False

        param = self._parameter_for(xml="""
            <param name="col1" type="data_column" data_ref="input1" use_header_names="true" numerical="true" force_select="false">
            </param>
        """)
        assert param.data_ref == "input1"
        assert param.usecolnames is True
        assert param.force_select is False
        assert param.numerical is True

    def test_data_param_no_validation(self):
        param = self._parameter_for(xml="""
            <param name="input" type="data">
            </param>
        """)
        assert len(param.validators) == 1
        param = self._parameter_for(xml="""
            <param name="input" type="data" no_validation="true">
            </param>
        """)
        assert len(param.validators) == 0

    def test_data_param_dynamic_options(self):
        param = self._parameter_for(xml="""
            <param name="input" type="data" />
        """)
        assert param.options is None
        assert param.options_filter_attribute is None

        param = self._parameter_for(xml="""
            <param name="input" type="data">
                <options from_data_table="cow">
                </options>
            </param>
        """)
        assert param.options is not None
        assert param.options_filter_attribute is None

        param = self._parameter_for(xml="""
            <param name="input" type="data">
                <options from_data_table="cow" options_filter_attribute="cow">
                </options>
            </param>
        """)
        assert param.options is not None
        assert param.options_filter_attribute == "cow"

    def test_conversions(self):
        param = self._parameter_for(xml="""
            <param name="input" type="data" />
        """)
        assert param.conversions == []

        param = self._parameter_for(xml="""
            <param name="input" type="data">
                <conversion name="foo" type="txt" />
                <conversion name="foo2" type="bam" />
            </param>
        """)
        assert param.conversions[0][0] == "foo"
        assert param.conversions[0][1] == "txt"
        assert param.conversions[1][0] == "foo2"
        assert param.conversions[1][1] == "bam"

    def test_drilldown(self):
        param = self._parameter_for(xml="""
            <param name="some_name" type="drill_down" display="checkbox" hierarchy="recurse" multiple="true">
              <options>
               <option name="Heading 1" value="heading1">
                   <option name="Option 1" value="option1"/>
                   <option name="Option 2" value="option2"/>
                   <option name="Heading 1" value="heading1">
                     <option name="Option 3" value="option3"/>
                     <option name="Option 4" value="option4"/>
                   </option>
               </option>
               <option name="Option 5" value="option5"/>
              </options>
            </param>
        """)
        assert param.type == "drill_down"
        assert param.name == "some_name"
        assert param.options

        heading1 = param.options[0]
        assert heading1["selected"] is False
        assert heading1["name"] == "Heading 1"
        assert heading1["value"] == "heading1"
        option1 = heading1["options"][0]
        assert option1["selected"] is False
        assert option1["name"] == "Option 1"
        assert option1["value"] == "option1"

        option5 = param.options[1]
        assert option5["selected"] is False
        assert option5["name"] == "Option 5"
        assert option5["value"] == "option5"
        assert len(option5["options"]) == 0

    def test_tool_collection(self):
        param = self._parameter_for(xml="""
            <param name="datac" type="data_collection" collection_type="list" format="txt">
            </param>
        """)
        assert param.type == "data_collection"
        assert param.collection_type == "list"

    def test_library(self):
        param = self._parameter_for(xml="""
            <param name="libraryp" type="library_data">
            </param>
        """)
        assert param.type == "library_data"
        assert param.name == "libraryp"
