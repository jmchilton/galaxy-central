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
