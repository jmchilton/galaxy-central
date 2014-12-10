from .interface import ToolSource
from .interface import PagesSource
from galaxy.tools.deps import requirements
from galaxy.tools.parameters import output_collect
import galaxy.tools


class YamlToolSource(ToolSource):

    def __init__(self, root_dict):
        self.root_dict = root_dict

    def parse_id(self):
        return self.root_dict.get("id")

    def parse_version(self):
        return self.root_dict.get("version")

    def parse_name(self):
        return self.root_dict.get("name")

    def parse_description(self):
        return self.root_dict.get("description")

    def parse_is_multi_byte(self):
        return self.root_dict.get("is_multi_byte", self.default_is_multi_byte)

    def parse_display_interface(self, default):
        return self.root_dict.get('display_interface', default)

    def parse_require_login(self, default):
        return self.root_dict.get('require_login', default)

    def parse_command(self):
        return self.root_dict.get("command")

    def parse_interpreter(self):
        return self.root_dict.get("interpreter")

    def parse_version_command(self):
        return self.root_dict.get("runtime_version", {}).get("command", None)

    def parse_version_command_interpreter(self):
        return self.root_dict.get("runtime_version", {}).get("interpreter", None)

    def parse_requirements_and_containers(self):
        return requirements.parse_requirements_from_dict(self.root_dict)

    def parse_input_pages(self):
        return PagesSource([])

    def parse_stdio(self):
        from galaxy.jobs.error_level import StdioErrorLevel

        # New format - starting out just using exit code.
        exit_code_lower = galaxy.tools.ToolStdioExitCode()
        exit_code_lower.range_start = float("-inf")
        exit_code_lower.range_end = -1
        exit_code_lower.error_level = StdioErrorLevel.FATAL
        exit_code_high = galaxy.tools.ToolStdioExitCode()
        exit_code_high.range_start = 1
        exit_code_high.range_end = float("inf")
        exit_code_lower.error_level = StdioErrorLevel.FATAL
        return [exit_code_lower, exit_code_high], []

    def parse_outputs(self, tool):
        outputs = self.root_dict.get("outputs", {})
        output_defs = []
        for name, output_dict in outputs.items():
            output_defs.append(self._parse_output(tool, name, output_dict))
        return output_defs

    def _parse_output(self, tool, name, output_dict):
        # TODO: handle filters, actions, change_format
        output = galaxy.tools.ToolOutput( name )
        output.format = output_dict.get("format", "data")
        output.change_format = []
        output.format_source = output_dict.get("format_source", None)
        output.metadata_source = output_dict.get("metadata_source", "")
        output.parent = output_dict.get("parent", None)
        output.label = output_dict.get( "label", None )
        output.count = output_dict.get("count", 1)
        output.filters = []
        output.tool = tool
        output.from_work_dir = output_dict.get("from_work_dir", None)
        output.hidden = output_dict.get("hidden", "")
        output.actions = galaxy.tools.ToolOutputActionGroup( output, None )
        discover_datasets_dicts = output_dict.get( "discover_datasets", [] )
        if isinstance( discover_datasets_dicts, dict ):
            discover_datasets_dicts = [ discover_datasets_dicts ]
        output.dataset_collectors = output_collect.dataset_collectors_from_list( discover_datasets_dicts )
        return output
