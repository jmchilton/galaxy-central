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
        if not out_elem:
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
