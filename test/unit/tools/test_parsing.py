import os.path
import tempfile
import shutil

from galaxy.tools.parser.factory import get_tool_source
from galaxy.tools.imp_exp import EXPORT_HISTORY_TEXT

import unittest


TOOL_XML_1 = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true">
</tool>
"""

TOOL_YAML_1 = """
name: "Bowtie Mapper"
id: bowtie
version: 1.0.2
"""


class BaseLoaderTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_directory)

    @property
    def _tool_source(self):
        path = os.path.join(self.temp_directory, self.source_file_name)
        open(path, "w").write(self.source_contents)
        tool_source = get_tool_source(path)
        return tool_source


class XmlLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "bwa.xml"
    source_contents = TOOL_XML_1

    def test_version(self):
        assert self._tool_source.parse_version() == "1.0.1"

    def test_id(self):
        assert self._tool_source.parse_id() == "bwa"

    def test_module_and_type(self):
        assert self._tool_source.parse_tool_module() is None
        assert self._tool_source.parse_tool_type() is None

    def test_name(self):
        assert self._tool_source.parse_name() == "BWA Mapper"

    def test_is_multi_byte(self):
        assert self._tool_source.parse_is_multi_byte()


class YamlLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "bwa.yml"
    source_contents = TOOL_YAML_1

    def test_version(self):
        assert self._tool_source.parse_version() == "1.0.2"

    def test_id(self):
        assert self._tool_source.parse_id() == "bowtie"

    def test_module_and_type(self):
        # These just rely on defaults
        assert self._tool_source.parse_tool_module() is None
        assert self._tool_source.parse_tool_type() is None

    def test_name(self):
        assert self._tool_source.parse_name() == "Bowtie Mapper"

    def test_is_multi_byte(self):
        assert not self._tool_source.parse_is_multi_byte()


class DataSourceLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "ds.xml"
    source_contents = """<?xml version="1.0"?>
<tool name="YeastMine" id="yeastmine" tool_type="data_source">
    <description>server</description>
    <command interpreter="python">data_source.py $output $__app__.config.output_size_limit</command>
    <inputs action="http://yeastmine.yeastgenome.org/yeastmine/begin.do" check_values="false" method="get">
        <display>go to yeastMine server $GALAXY_URL</display>
    </inputs>
    <request_param_translation>
        <request_param galaxy_name="data_type" remote_name="data_type" missing="auto" >
            <value_translation>
                <value galaxy_value="auto" remote_value="txt" /> <!-- intermine currently always provides 'txt', make this auto detect -->
            </value_translation>
        </request_param>
    </request_param_translation>
    <uihints minwidth="800"/>
    <outputs>
        <data name="output" format="txt" />
    </outputs>
    <options sanitize="False" refresh="True"/>
</tool>
"""

    def test_tool_type(self):
        assert self._tool_source.parse_tool_type() == "data_source"


class SpecialToolLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "export.xml"
    source_contents = EXPORT_HISTORY_TEXT

    def test_tool_type(self):
        tool_module = self._tool_source.parse_tool_module()
        # Probably we don't parse_tool_module any more? -
        # tool_type seems sufficient.
        assert tool_module[0] == "galaxy.tools"
        assert tool_module[1] == "ExportHistoryTool"
        assert self._tool_source.parse_tool_type() == "export_history"

    def test_is_multi_byte(self):
        assert not self._tool_source.parse_is_multi_byte()
