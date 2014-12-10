from .interface import ToolSource


class YamlToolSource(ToolSource):

    def __init__(self, root_dict):
        self.root_dict = root_dict

    def parse_id(self):
        return self.root_dict.get("id")

    def parse_version(self):
        return self.root_dict.get("version")

    def parse_name(self):
        return self.root_dict.get("name")

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
