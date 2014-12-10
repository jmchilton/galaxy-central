from .interface import ToolSource
from galaxy.util import string_as_bool, xml_text


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
