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
                lineage = SingletonLineage(tool_id)
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


class SingletonLineage(ToolLineage):
    """ Single stand-alone tool - with no lineage.
    """

    def __init__(self, tool_id, **kwds):
        self.tool_id = tool_id

    def get_version_ids( self, reverse=False ):
        return [self.tool_id]


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


def get_install_tool_version( app, tool_id ):
    return app.install_model.context.query(
        app.install_model.ToolVersion
    ).filter(
        app.install_model.ToolVersion.table.c.tool_id == tool_id
    ).first()


__all__ = ["LineageMap"]
