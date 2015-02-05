import os
from xml.etree.ElementTree import XML
from unittest import TestCase

from galaxy.model import Job
from galaxy.model import History
from galaxy.model import Dataset
from galaxy.model import JobParameter
from galaxy.model import HistoryDatasetAssociation
from galaxy.model import JobToInputDatasetAssociation
from galaxy.tools.evaluation import ToolEvaluator
from galaxy.jobs import SimpleComputeEnvironment
from galaxy.jobs.datasets import DatasetPath
from galaxy.util.bunch import Bunch

# For MockTool
from galaxy.tools.parameters import params_from_strings
from galaxy.tools import ToolOutput
from galaxy.tools.parameters.grouping import Repeat
from galaxy.tools.parameters.grouping import Conditional
from galaxy.tools.parameters.grouping import ConditionalWhen
from galaxy.tools.parameters.basic import IntegerToolParameter
from galaxy.tools.parameters.basic import SelectToolParameter
from galaxy.tools.parameters.basic import DataToolParameter


# Test fixtures for Galaxy infrastructure.
from tools_support import UsesApp

# To Test:
# - param_file handling.
TEST_TOOL_DIRECTORY = "/path/to/the/tool"


class ToolEvaluatorTestCase(TestCase, UsesApp):

    def setUp(self):
        self.setup_app()
        self.tool = MockTool(self.app)
        self.job = Job()
        self.job.history = History()
        self.job.parameters = [ JobParameter( name="thresh", value="4" ) ]
        self.evaluator = ToolEvaluator( self.app, self.tool, self.job, self.test_directory )

    def tearDown(self):
        self.tear_down_app()

    def test_simple_evaluation( self ):
        self._setup_test_bwa_job()
        self._set_compute_environment()
        command_line, extra_filenames = self.evaluator.build( )
        self.assertEquals( command_line, "bwa --thresh=4 --in=/galaxy/files/dataset_1.dat --out=/galaxy/files/dataset_2.dat" )

    def test_repeat_evaluation( self ):
        repeat = Repeat()
        repeat.name = "r"
        repeat.inputs = { "thresh": self.tool.test_thresh_param() }
        self.tool.set_params( { "r": repeat } )
        self.job.parameters = [ JobParameter( name="r", value='''[{"thresh": 4, "__index__": 0},{"thresh": 5, "__index__": 1}]''' ) ]
        self.tool._command_line = "prog1 #for $r_i in $r # $r_i.thresh#end for#"
        self._set_compute_environment()
        command_line, extra_filenames = self.evaluator.build( )
        self.assertEquals( command_line, "prog1  4 5" )

    def test_conditional_evaluation( self ):
        select_xml = XML('''<param name="always_true" type="select"><option value="true">True</option></param>''')
        parameter = SelectToolParameter( self.tool, select_xml )

        conditional = Conditional()
        conditional.name = "c"
        conditional.test_param = parameter
        when = ConditionalWhen()
        when.inputs = { "thresh": self.tool.test_thresh_param() }
        when.value = "true"
        conditional.cases = [ when ]
        self.tool.set_params( { "c": conditional } )
        self.job.parameters = [ JobParameter( name="c", value='''{"thresh": 4, "always_true": "true", "__current_case__": 0}''' ) ]
        self.tool._command_line = "prog1 --thresh=${c.thresh} --test_param=${c.always_true}"
        self._set_compute_environment()
        command_line, extra_filenames = self.evaluator.build( )
        self.assertEquals( command_line, "prog1 --thresh=4 --test_param=true" )

    def test_evaluation_of_optional_datasets( self ):
        # Make sure optional dataset don't cause evaluation to break and
        # evaluate in cheetah templates as 'None'.
        select_xml = XML('''<param name="input1" type="data" optional="true"></param>''')
        parameter = DataToolParameter( self.tool, select_xml )
        self.job.parameters = [ JobParameter( name="input1", value=u'null' ) ]
        self.tool.set_params( { "input1": parameter } )
        self.tool._command_line = "prog1 --opt_input='${input1}'"
        self._set_compute_environment()
        command_line, extra_filenames = self.evaluator.build( )
        self.assertEquals( command_line, "prog1 --opt_input='None'" )

    def test_evaluation_with_path_rewrites_wrapped( self ):
        self.tool.check_values = True
        self.__test_evaluation_with_path_rewrites()

    def test_evaluation_with_path_rewrites_unwrapped( self ):
        self.tool.check_values = False
        self.__test_evaluation_with_path_rewrites()

    def __test_evaluation_with_path_rewrites( self ):
        # Various things can cause dataset paths to be rewritten (Task
        # splitting, config.outputs_to_working_directory). This tests that
        #functionality.
        self._setup_test_bwa_job()
        job_path_1 = "%s/dataset_1.dat" % self.test_directory
        job_path_2 = "%s/dataset_2.dat" % self.test_directory
        self._set_compute_environment(
            input_paths=[DatasetPath(1, '/galaxy/files/dataset_1.dat', false_path=job_path_1)],
            output_paths=[DatasetPath(2, '/galaxy/files/dataset_2.dat', false_path=job_path_2)],
        )
        command_line, extra_filenames = self.evaluator.build( )
        self.assertEquals( command_line, "bwa --thresh=4 --in=%s --out=%s" % (job_path_1, job_path_2) )

    def test_configfiles_evaluation( self ):
        self.tool.config_files.append( ( "conf1", None, "$thresh" ) )
        self.tool._command_line = "prog1 $conf1"
        self._set_compute_environment()
        command_line, extra_filenames = self.evaluator.build( )
        self.assertEquals( len( extra_filenames ), 1)
        config_filename = extra_filenames[ 0 ]
        config_basename = os.path.basename( config_filename )
        # Verify config file written into working directory.
        self.assertEquals( os.path.join( self.test_directory, config_basename ), config_filename )
        # Verify config file contents are evaluated against parameters.
        assert open( config_filename, "r").read() == "4"
        self.assertEquals(command_line, "prog1 %s" % config_filename)

    def test_arbitrary_path_rewriting_wrapped( self ):
        self.tool.check_values = True
        self.__test_arbitrary_path_rewriting()

    def test_arbitrary_path_rewriting_unwrapped( self ):
        self.tool.check_values = False
        self.__test_arbitrary_path_rewriting()

    def __test_arbitrary_path_rewriting( self ):
        self.job.parameters = [ JobParameter( name="index_path", value="\"/old/path/human\"" ) ]
        xml = XML('''<param name="index_path" type="select">
            <option value="/old/path/human">Human</option>
            <option value="/old/path/mouse">Mouse</option>
        </param>''')
        parameter = SelectToolParameter( self.tool, xml )

        def get_field_by_name_for_value( name, value, trans, other_values ):
            assert value == "/old/path/human"
            assert name == "path"
            return ["/old/path/human"]

        parameter.options = Bunch(get_field_by_name_for_value=get_field_by_name_for_value)
        self.tool.set_params( {
            "index_path": parameter
        } )
        self.tool._command_line = "prog1 $index_path.fields.path"

        def test_path_rewriter(v):
            if v:
                v = v.replace("/old", "/new")
            return v
        self._set_compute_environment(path_rewriter=test_path_rewriter)
        command_line, extra_filenames = self.evaluator.build( )
        self.assertEquals(command_line, "prog1 /new/path/human")

    def test_template_property_app( self ):
        self._assert_template_property_is("$__app__.config.new_file_path", self.app.config.new_file_path)

    def test_template_property_new_file_path( self ):
        self._assert_template_property_is("$__new_file_path__", self.app.config.new_file_path)

    def test_template_property_root_dir( self ):
        self._assert_template_property_is("$__root_dir__", self.app.config.root)

    def test_template_property_admin_users( self ):
        self._assert_template_property_is("$__admin_users__", "mary@example.com")

    def _assert_template_property_is(self, expression, value):
        self.tool._command_line = "test.exe"
        self.tool.config_files.append( ( "conf1", None, """%s""" % expression) )
        self._set_compute_environment()
        _, extra_filenames = self.evaluator.build( )
        config_filename = extra_filenames[ 0 ]
        self.assertEquals(open( config_filename, "r").read(), value)

    def _set_compute_environment(self, **kwds):
        if "working_directory" not in kwds:
            kwds[ "working_directory" ] = self.test_directory
        if "new_file_path" not in kwds:
            kwds[ "new_file_path" ] = self.app.config.new_file_path
        self.evaluator.set_compute_environment( TestComputeEnviornment( **kwds ) )
        assert "exec_before_job" in self.tool.hooks_called

    def _setup_test_bwa_job( self ):
        self.job.input_datasets = [ self._job_dataset( 'input1', '/galaxy/files/dataset_1.dat' ) ]
        self.job.output_datasets = [ self._job_dataset( 'output1', '/galaxy/files/dataset_2.dat' ) ]

    def _job_dataset( self, name, path ):
        metadata = dict( )
        hda = HistoryDatasetAssociation( name=name, metadata=metadata )
        hda.dataset = Dataset( id=123, external_filename=path )
        hda.dataset.metadata = dict()
        hda.children = []
        jida = JobToInputDatasetAssociation( name=name, dataset=hda )
        return jida


class MockHistoryDatasetAssociation( HistoryDatasetAssociation ):

    def __init__( self, **kwds ):
        self._metadata = dict()
        super( MockHistoryDatasetAssociation, self ).__init__( **kwds )


class TestComputeEnviornment( SimpleComputeEnvironment ):

    def __init__(
        self,
        new_file_path,
        working_directory,
        input_paths=[ '/galaxy/files/dataset_1.dat' ],
        output_paths=[ '/galaxy/files/dataset_2.dat' ],
        path_rewriter=None
    ):
        self._new_file_path = new_file_path
        self._working_directory = working_directory
        self._input_paths = input_paths
        self._output_paths = output_paths
        self._path_rewriter = path_rewriter

    def input_paths( self ):
        return self._input_paths

    def output_paths( self ):
        return self._output_paths

    def working_directory( self ):
        return self._working_directory

    def new_file_path(self):
        return self._new_file_path

    def unstructured_path_rewriter(self):
        if self._path_rewriter:
            return self._path_rewriter
        else:
            return super(TestComputeEnviornment, self).unstructured_path_rewriter()

    def tool_directory( self ):
        return TEST_TOOL_DIRECTORY


class MockTool( object ):

    def __init__( self, app ):
        self.app = app
        self.hooks_called = []
        self._config_files = []
        self._command_line = "bwa --thresh=$thresh --in=$input1 --out=$output1"
        self._params = { "thresh": self.test_thresh_param() }
        self.options = Bunch(sanitize=False)
        self.check_values = True

    def test_thresh_param( self ):
        elem = XML( '<param name="thresh" type="integer" value="5" />' )
        return IntegerToolParameter( self, elem )

    def params_from_strings( self, params, app, ignore_errors=False ):
        return params_from_strings( self.inputs, params, app, ignore_errors )

    @property
    def template_macro_params( self ):
        return {}

    @property
    def inputs( self ):
        return self._params

    def set_params( self, params ):
        self._params = params

    @property
    def outputs( self ):
        #elem_output1 = XML( '<param name="output1" type="data" format="txt"/>' )
        #                DataToolParameter( self, elem_output1 ),
        return dict(
            output1=ToolOutput( "output1" ),
        )

    @property
    def config_files( self ):
        return self._config_files

    @property
    def command( self ):
        return self._command_line

    @property
    def interpreter( self ):
        return None

    def handle_unvalidated_param_values( self, input_values, app ):
        pass

    def build_param_dict( self, incoming, *args, **kwds ):
        return incoming

    def call_hook( self, hook_name, *args, **kwargs ):
        self.hooks_called.append( hook_name )

    def exec_before_job( self, *args, **kwargs ):
        pass
