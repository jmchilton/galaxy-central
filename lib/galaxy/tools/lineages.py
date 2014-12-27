import threading
from distutils.version import LooseVersion

from abc import ABCMeta
from abc import abstractmethod


class LineageMap(object):
    """ Map each unique tool id to a lineage object.
    """

    def __init__(self, app):
        self.lineage_map = {}
        self.app = app

    def register(self, tool, **kwds):
        tool_id = tool.id
        if tool_id not in self.lineage_map:
            tool_shed_repository = kwds.get("tool_shed_repository", None)
            if tool_shed_repository:
                lineage = ToolShedLineage.from_tool(self.app, tool, tool_shed_repository)
            else:
                lineage = StockLineage.for_tool_id(tool_id)
                lineage.register_version( tool.version )
            self.lineage_map[tool_id] = lineage
        return self.lineage_map[tool_id]

    def get(self, tool_id):
        if tool_id not in self.lineage_map:
            lineage = ToolShedLineage.from_tool_id( self.app, tool_id )
            if lineage:
                self.lineage_map[tool_id] = lineage

        return self.lineage_map.get(tool_id, None)


class ToolLineage(object):
    """
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_version_ids( self, reverse=False ):
        """ Return an ordered list of lineages in this chain, from
        oldest to newest.
        """

    @abstractmethod
    def get_versions( self, reverse=False ):
        """ Return an ordered list of lineages (ToolLineageVersion) in this
        chain, from oldest to newest.
        """


class ToolLineageVersion(object):
    """ Represents a single tool in a lineage. If lineage is based
    around GUIDs that somehow encode the version (either using GUID
    or a simple tool id and a version). """
    
    def __init__(self, id, version):
        self.id = id
        self.version = version

    @staticmethod
    def from_id_and_verion( self, id, version ):
        assert version is not None
        return ToolLineageVersion( id, version )

    @staticmethod
    def from_guid( self, guid ):
        return ToolLineageVersion( guid, None )

    @property
    def id_based( self ):
        """ Return True if the lineage is defined by GUIDs (in this
        case the indexer of the tools (i.e. the ToolBox) should ignore
        the tool_version (because it is encoded in the GUID and managed
        externally).
        """
        return self.version is None


class StockLineage(ToolLineage):
    """ Single stand-alone tool - with no lineage.
    """
    lineages_by_id = {}
    lock = threading.Lock()

    def __init__(self, tool_id, **kwds):
        self.tool_id = tool_id
        self.tool_versions = set()

    def get_version_ids( self, reverse=False ):
        return [self.tool_id]

    @staticmethod
    def for_tool_id( tool_id ):
        lineages_by_id = StockLineage.lineages_by_id
        with StockLineage.lock:
            if tool_id not in lineages_by_id:
                lineages_by_id[ tool_id ] = StockLineage( tool_id )
        return lineages_by_id[ tool_id ]

    def register_version( self, tool_version ):
        assert tool_version is not None
        self.tool_versions.add( tool_version )

    def get_versions( self, reverse=False ):
        versions = [ ToolLineageVersion( self.tool_id, v ) for v in self.tool_versions ]
        sorted( versions, key=StockLineage._compare )

    @staticmethod
    def _compare( tool_lineage_version_1, tool_lineage_version_2 ):
        v1 = LooseVersion( tool_lineage_version_1.version )
        v2 = LooseVersion( tool_lineage_version_2.version )
        return v1.__cmp__( v2 )


class ToolShedLineage(ToolLineage):
    """ Representation of tool lineage derived from tool shed repository
    installations. """

    def __init__(self, app, tool_version):
        self.app = app
        self.tool_version = tool_version

    @staticmethod
    def from_tool( app, tool, tool_shed_repository ):
        # Make sure the tool has a tool_version.
        if not get_install_tool_version( app, tool.id ):
            tool_version = app.install_model.ToolVersion( tool_id=tool.id, tool_shed_repository=tool_shed_repository )
            app.install_model.context.add( tool_version )
            app.install_model.context.flush()
        return ToolShedLineage( app, tool.tool_version )

    @staticmethod
    def from_tool_id( app, tool_id ):
        tool_version = get_install_tool_version( app, tool_id )
        if tool_version:
            return ToolShedLineage( app, tool_version )
        else:
            return None

    def get_version_ids( self, reverse=False ):
        return self.tool_version.get_version_ids( self.app, reverse=reverse )

    def get_versions( self, reverse=False ):
        return map( ToolLineageVersion.from_guid, self.get_version_ids( reverse=reverse ) )


def get_install_tool_version( app, tool_id ):
    return app.install_model.context.query(
        app.install_model.ToolVersion
    ).filter(
        app.install_model.ToolVersion.table.c.tool_id == tool_id
    ).first()


__all__ = ["LineageMap"]
