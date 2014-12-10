from abc import ABCMeta
from abc import abstractmethod


class ToolSource(object):
    """ This interface represents an abstract source to parse tool
    information from.
    """
    __metaclass__ = ABCMeta
    default_is_multi_byte = False

    @abstractmethod
    def parse_id(self):
        """ Parse an ID describing the abstract tool. This is not the
        GUID tracked by the tool shed but the simple id (there may be
        multiple tools loaded in Galaxy with this same simple id).
        """

    @abstractmethod
    def parse_version(self):
        """ Parse a version describing the abstract tool.
        """

    def parse_tool_module(self):
        """ Load Tool class from a custom module. (Optional).

        If not None, return pair containing module and class (as strings).
        """
        return None

    def parse_tool_type(self):
        """ Load simple tool type string (e.g. 'data_source', 'default').
        """
        return None

    @abstractmethod
    def parse_name(self):
        """ Parse a short name for tool (required). """

    @abstractmethod
    def parse_description(self):
        """ Parse a description for tool. Longer than name, shorted than help. """

    def parse_is_multi_byte(self):
        """ Parse is_multi_byte from tool - TODO: figure out what this is and
        document.
        """
        return self.default_is_multi_byte

    def parse_display_interface(self, default):
        """ Parse display_interface - fallback to default for the tool type
        (supplied as default parameter) if not specified.
        """
        return default

    def parse_require_login(self, default):
        """ Parse whether the tool requires login (as a bool).
        """
        return default

    def parse_request_param_translation_elem(self):
        """ Return an XML element describing require parameter translation.

        If we wish to support this feature for non-XML based tools this should
        be converted to return some sort of object interface instead of a RAW
        XML element.
        """
        return None

    @abstractmethod
    def parse_command(self):
        """ Return string contianing command to run.
        """

    @abstractmethod
    def parse_interpreter(self):
        """ Return string containing the interpreter to prepend to the command
        (for instance this might be 'python' to run a Python wrapper located
        adjacent to the tool).
        """

    def parse_redirect_url_params_elem(self):
        """ Return an XML element describing redirect_url_params.

        If we wish to support this feature for non-XML based tools this should
        be converted to return some sort of object interface instead of a RAW
        XML element.
        """
        return None

    def parse_version_command(self):
        """ Parse command used to determine version of primary application
        driving the tool. Return None to not generate or record such a command.
        """
        return None

    def parse_version_command_interpreter(self):
        """ Parse command used to determine version of primary application
        driving the tool. Return None to not generate or record such a command.
        """
        return None

    def parse_parallelism(self):
        """ Return a galaxy.jobs.ParallismInfo object describing task splitting
        or None.
        """
        return None
