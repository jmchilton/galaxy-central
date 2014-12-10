from .interface import ToolSource


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

    def parse_tool_type(self):
        root = self.root
        if root.get( 'tool_type', None ) is not None:
            return root.get( 'tool_type' )

    def parse_name(self):
        return self.root.get( "name" )
