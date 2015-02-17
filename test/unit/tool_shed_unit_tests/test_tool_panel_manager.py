import os

from galaxy.util import parse_xml

from tools.test_toolbox import BaseToolBoxTestCase
from tool_shed.galaxy_install.tools import tool_panel_manager

from tool_shed.tools import tool_version_manager

DEFAULT_GUID = "123456"


class ToolPanelManagerTestCase( BaseToolBoxTestCase ):

    def test_handle_tool_panel_section( self ):
        self._init_tool()
        self._add_config( """<toolbox><section id="tid" name="test"><tool file="tool.xml" /></section></toolbox>""" )
        toolbox = self.toolbox
        tpm = self.tpm
        # Test fetch existing section by id.
        section_id, section = tpm.handle_tool_panel_section( toolbox, tool_panel_section_id="tid" )
        assert section_id == "tid"
        assert len( section.elems ) == 1  # tool.xml
        assert section.id == "tid"
        assert len( toolbox._tool_panel ) == 1

        section_id, section = tpm.handle_tool_panel_section( toolbox, new_tool_panel_section_label="tid2" )
        assert section_id == "tid2"
        assert len( section.elems ) == 0  # new section
        assert section.id == "tid2"
        assert len( toolbox._tool_panel ) == 2

        # Test re-fetch new section by same id.
        section_id, section = tpm.handle_tool_panel_section( toolbox, new_tool_panel_section_label="tid2" )
        assert section_id == "tid2"
        assert len( section.elems ) == 0  # new section
        assert section.id == "tid2"
        assert len( toolbox._tool_panel ) == 2

    def test_add_tool_to_panel( self ):
        self._init_ts_tool( guid=DEFAULT_GUID )
        self._init_dynamic_tool_conf()
        tool_path = self._tool_path()
        new_tools = [{"guid": DEFAULT_GUID, "tool_config": tool_path}]
        repository_tools_tups = [
            (
                tool_path,
                DEFAULT_GUID,
                self.tool,
            )
        ]
        _, section = self.toolbox.get_section("tid1", create_if_needed=True)
        tpm = self.tpm
        tool_panel_dict = tpm.generate_tool_panel_dict_for_new_install(
            tool_dicts=new_tools,
            tool_section=section,
        )
        tpm.add_to_tool_panel(
            repository_name="test_repo",
            repository_clone_url="http://github.com/galaxyproject/example.git",
            changeset_revision="0123456789abcde",
            repository_tools_tups=repository_tools_tups,
            owner="devteam",
            shed_tool_conf="tool_conf.xml",
            tool_panel_dict=tool_panel_dict,
        )
        self._verify_tool_confs()

    def test_add_twice( self ):
        self._init_dynamic_tool_conf()
        tool_versions = {}
        previous_guid = None
        for v in "1", "2", "3":
            changeset = "0123456789abcde%s" % v
            guid = DEFAULT_GUID + ("v%s" % v)
            tool = self._init_ts_tool( guid=guid, filename="tool_v%s.xml" % v )
            tool_path = self._tool_path( name="tool_v%s.xml" % v )
            new_tools = [{"guid": guid, "tool_config": tool_path}]
            tool_shed_repository = self._repo_install( changeset )
            repository_tools_tups = [
                (
                    tool_path,
                    guid,
                    tool,
                )
            ]
            _, section = self.toolbox.get_section("tid1", create_if_needed=True)
            tpm = self.tpm
            tool_panel_dict = tpm.generate_tool_panel_dict_for_new_install(
                tool_dicts=new_tools,
                tool_section=section,
            )
            if previous_guid:
                tool_versions[ guid ] = previous_guid
            self.tvm.handle_tool_versions( [tool_versions], tool_shed_repository )
            tpm.add_to_tool_panel(
                repository_name="example",
                repository_clone_url="github.com",
                changeset_revision=changeset,
                repository_tools_tups=repository_tools_tups,
                owner="galaxyproject",
                shed_tool_conf="tool_conf.xml",
                tool_panel_dict=tool_panel_dict,
            )
            self._verify_tool_confs()
            section = self.toolbox._tool_panel["tid1"]
            # New GUID replaced old one in tool panel but both
            # appear in integrated tool panel.
            if previous_guid:
                assert ("tool_%s" % previous_guid) not in section.panel_items()
            assert ("tool_%s" % guid) in self.toolbox._integrated_tool_panel["tid1"].panel_items()
            previous_guid = guid

    def test_deactivate_in_section( self ):
        self._setup_two_versions_remove_one( section=True, uninstall=False )
        self._verify_version_2_removed_from_panel( )
        # Still in tool conf since not uninstalled only deactivated...
        assert "github.com/galaxyproject/example/test_tool/0.2" in open(os.path.join(self.test_directory, "tool_conf.xml"), "r").read()
        self._verify_tool_confs()

        self._remove_guids( ["github.com/galaxyproject/example/test_tool/0.1"], uninstall=False )

        # Now no versions of this tool are returned by toolbox.
        all_versions = self.toolbox.get_tool( "test_tool", get_all_versions=True )
        assert not all_versions

        # Check that tool panel has reverted to old value...
        section = self.toolbox._tool_panel["tid"]
        assert len(section.elems) == 0

    def test_uninstall_in_section( self ):
        self._setup_two_versions_remove_one( section=True, uninstall=True )
        self._verify_version_2_removed_from_panel( )
        # Not in tool conf because it was uninstalled.
        assert "github.com/galaxyproject/example/test_tool/0.2" not in open(os.path.join(self.test_directory, "tool_conf.xml"), "r").read()
        assert "tool_github.com/galaxyproject/example/test_tool/0.2" not in self.toolbox._integrated_tool_panel["tid"].elems
        self._verify_tool_confs()

    def test_deactivate_outside_section( self ):
        self._setup_two_versions_remove_one( section=False, uninstall=False )
        self._verify_version_2_removed_from_panel( section=False )
        # Still in tool conf since not uninstalled only deactivated...
        assert "github.com/galaxyproject/example/test_tool/0.2" in open(os.path.join(self.test_directory, "tool_conf.xml"), "r").read()
        self._verify_tool_confs()

    def test_uninstall_outside_section( self ):
        self._setup_two_versions_remove_one( section=False, uninstall=True )
        self._verify_version_2_removed_from_panel( section=False )
        # Still in tool conf since not uninstalled only deactivated...
        assert "github.com/galaxyproject/example/test_tool/0.2" not in open(os.path.join(self.test_directory, "tool_conf.xml"), "r").read()
        self._verify_tool_confs()

        self._remove_guids( ["github.com/galaxyproject/example/test_tool/0.1"], uninstall=True )

        # Now no versions of this tool are returned by toolbox.
        all_versions = self.toolbox.get_tool( "test_tool", get_all_versions=True )
        assert not all_versions

        # Check that tool panel has reverted to old value...
        section = self.toolbox._tool_panel["tid"]
        assert len(section.elems) == 0

    def _setup_two_versions_remove_one( self, section, uninstall ):
        self._init_tool()
        self._setup_two_versions_in_config( section=True )
        self._setup_two_versions()
        self.toolbox
        self._remove_guids( ["github.com/galaxyproject/example/test_tool/0.2"], uninstall=uninstall )

    def _verify_version_2_removed_from_panel( self, section=True ):
        # Check that test_tool now only has one version...
        all_versions = self.toolbox.get_tool( "test_tool", get_all_versions=True )
        assert len( all_versions ) == 1

        # Check that tool panel has reverted to old value...
        if section:
            section = self.toolbox._tool_panel["tid"]
            assert len(section.elems) == 1
            assert section.elems.values()[0].id == "github.com/galaxyproject/example/test_tool/0.1"

            assert "github.com/galaxyproject/example/test_tool/0.2" not in self.toolbox._integrated_tool_panel["tid"].elems
        else:
            self.toolbox._tool_panel.values()[0].id == "github.com/galaxyproject/example/test_tool/0.1"
            assert "github.com/galaxyproject/example/test_tool/0.2" not in self.toolbox._integrated_tool_panel

    def _remove_guids( self, guids, uninstall, shed_tool_conf="tool_conf.xml" ):
        self.tpm.remove_guids(
            guids_to_remove=guids,
            shed_tool_conf=shed_tool_conf,
            uninstall=uninstall,
        )

    def _verify_tool_confs( self ):
        self._assert_valid_xml( self.integerated_tool_panel_path )
        self._assert_valid_xml( os.path.join( self.test_directory, "tool_conf.xml" ) )

    def _assert_valid_xml( self, filename ):
        try:
            parse_xml( filename )
        except Exception:
            message_template = "file %s does not contain valid XML, content %s"
            message = message_template % ( filename, open( filename, "r" ).read() )
            raise AssertionError( message )

    def _init_dynamic_tool_conf( self ):
        # Add a dynamic tool conf (such as a ToolShed managed one) to list of configs.
        self._add_config( """<toolbox tool_path="%s"></toolbox>""" % self.test_directory )

    def _init_ts_tool( self, guid=DEFAULT_GUID, **kwds ):
        tool = self._init_tool( **kwds )
        tool.guid = guid
        return tool

    @property
    def tpm( self ):
        return tool_panel_manager.ToolPanelManager( self.app )

    @property
    def tvm( self ):
        return tool_version_manager.ToolVersionManager( self.app )
