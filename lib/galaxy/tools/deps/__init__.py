"""
Dependency management for tools.
"""

import os.path

import logging
log = logging.getLogger( __name__ )

from galaxy.util import parse_xml
import galaxy.tools.deps.resolvers

from .resolvers import INDETERMINATE_DEPENDENCY
from .resolvers.galaxy_packages import GalaxyPackageDependencyResolver
from .resolvers.tool_shed_packages import ToolShedPackageDependencyResolver


class DependencyManager( object ):
    """
    A DependencyManager attempts to resolve named and versioned dependencies by
    searching for them under a list of directories. Directories should be
    of the form:

        $BASE/name/version/...

    and should each contain a file 'env.sh' which can be sourced to make the
    dependency available in the current shell environment.
    """
    def __init__( self, default_base_path, conf_file=None ):
        """
        Create a new dependency manager looking for packages under the paths listed
        in `base_paths`.  The default base path is app.config.tool_dependency_dir.
        """
        if not os.path.exists( default_base_path ):
            log.warn( "Path '%s' does not exist, ignoring", default_base_path )
        if not os.path.isdir( default_base_path ):
            log.warn( "Path '%s' is not directory, ignoring", default_base_path )
        self.default_base_path = default_base_path
        self.resolver_classes = self.__resolvers_dict()
        self.dependency_resolvers = self.__build_dependency_resolvers( conf_file )

    def find_dep( self, name, version=None, type='package', **kwds ):
        for resolver in self.dependency_resolvers:
            dependency = resolver.resolve( name, version, type, **kwds )
            if dependency != INDETERMINATE_DEPENDENCY:
                return dependency
        return INDETERMINATE_DEPENDENCY

    def __build_dependency_resolvers( self, conf_file ):
        if not conf_file or not os.path.exists( conf_file ):
            return self.__default_dependency_resolvers()
        tree = parse_xml( conf_file )
        return self.__parse_resolver_conf_xml( tree )

    def __default_dependency_resolvers( self ):
        return [
            ToolShedPackageDependencyResolver(self),
            GalaxyPackageDependencyResolver(self),
        ]

    def __parse_resolver_conf_xml(self, tree):
        """

        :param tree: Object representing the root ``<dependency_resolvers>`` object in the file.
        :type tree: ``xml.etree.ElementTree.Element``
        """
        resolvers = []
        resolvers_element = tree.getroot()
        for resolver_element in resolvers_element.getchildren():
            resolver_type = resolver_element.tag
            resolver_kwds = dict(resolver_element.items())
            resolver = self.resolver_classes[resolver_type](self, **resolver_kwds)
            resolvers.append(resolver)
        return resolvers

    def __resolvers_dict( self ):
        resolver_dict = {}
        for resolver_module in self.__resolver_modules():
            for clazz in resolver_module.__all__:
                resolver_type = getattr(clazz, 'resolver_type', None)
                if resolver_type:
                    resolver_dict[resolver_type] = clazz
        return resolver_dict

    ## Utterly shameless copying and pasting between this and dynamic job
    ## runner code. TODO: Merge code bases and refactor in Carl's plugin
    ## framework.
    def __resolver_modules( self ):
        unsorted_module_names = self.__resolver_module_names( )
        module_names = sorted( unsorted_module_names, reverse=True )
        modules = []
        for resolver_module_name in module_names:
            try:
                module = __import__( resolver_module_name )
                for comp in resolver_module_name.split( "." )[1:]:
                    module = getattr( module, comp )
                modules.append( module )
            except BaseException, exception:
                exception_str = str( exception )
                message = "%s resolve module could not be loaded: %s" % ( resolver_module_name, exception_str )
                log.debug( message )
                continue
        return modules

    def __resolver_module_names( self ):
        resolvers_dir = galaxy.tools.deps.resolvers.__path__[0]
        names = []
        for fname in os.listdir( resolvers_dir ):
            if not( fname.startswith( "_" ) ) and fname.endswith( ".py" ):
                resolver_module_name = "galaxy.tools.deps.resolvers.%s" % fname[:-len(".py")]
                names.append( resolver_module_name )
        return names
