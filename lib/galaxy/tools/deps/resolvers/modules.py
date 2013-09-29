from os.path import exists, isdir, join
from StringIO import StringIO
from subprocess import Popen, PIPE

from ..resolvers import DependencyResolver, INDETERMINATE_DEPENDENCY, Dependency
from galaxy.util import string_as_bool

DEFAULT_MODULE_COMMAND = 'module'
DEFAULT_MODULE_DIRECTORY = '/usr/share/modules/modulefiles'
DEFAULT_INDICATOR = '(default)'
UNKNOWN_FIND_BY_MESSAGE = "ModuleDependencyResolver does not know how to find modules by [%s], find_by should be one of %s"


class ModuleDependencyResolver(DependencyResolver):
    resolver_type = "modules"

    def __init__(self, dependency_manager, **kwds):
        self.module_command = kwds.get('command', DEFAULT_MODULE_COMMAND)
        self.versionless = string_as_bool(kwds.get('versionless', 'false'))
        find_by = kwds.get('find_by', 'avail')
        if find_by == 'directory':
            directory = kwds.get('directory', DEFAULT_MODULE_DIRECTORY)
            self.module_checker = DirectoryModuleChecker(self, directory)
        elif find_by == 'avail':
            self.module_checker = AvailModuleChecker(self)
        else:
            raise Exception(UNKNOWN_FIND_BY_MESSAGE % (find_by, ["avail", "directory"]))

    def resolve( self, name, version, type, **kwds ):
        if type != "package":
            return INDETERMINATE_DEPENDENCY

        if self.versionless:
            version = None

        if self.__has_module(name, version):
            return ModuleDependency(self, name, version)

    def __has_module(self, name, version):
        return self.module_checker.has_module(name, version)


class DirectoryModuleChecker(object):

    def __init__(self, module_dependency_resolver, directory):
        self.module_dependency_resolver = module_dependency_resolver
        self.directory = directory

    def has_module(self, module, version):
        module_directory = join(self.directory, module)
        has_module_directory = isdir( join( self.directory, module ) )
        if not version:
            has_module = has_module_directory
        else:
            modulefile = join(  module_directory, version )
            has_modulefile = exists( modulefile )
            has_module = has_module_directory and has_modulefile
        return has_module


class AvailModuleChecker(object):

    def __init__(self, module_dependency_resolver):
        self.module_dependency_resolver = module_dependency_resolver

    def has_module(self, module, version):
        for module_name, module_version in self.__modules():
            names_match = module == module_name
            return names_match and (version == None or module_version == version)

    def __modules(self):
        raw_output = self.__module_avail_ouptut()
        for line in StringIO(raw_output):
            line = line and line.strip()
            if not line or line.startswith("-"):
                continue
            line_modules = line.split()
            for module in line_modules:
                if module.endswith(DEFAULT_INDICATOR):
                    module = module[0:-len(DEFAULT_INDICATOR)].strip()
                module_parts = module.split('/')
                module_version = None
                if len(module_parts) == 2:
                    module_version = module_parts[1]
                module_name = module_parts[0]
                yield module_name, module_version

    def __module_avail_ouptut(self):
        avail_command = '%s avail' % self.module_dependency_resolver.module_command
        return Popen([avail_command], shell=True, stderr=PIPE).communicate()[1]


class ModuleDependency(Dependency):

    def __init__(self, module_dependency_resolver, module_name, module_version=None):
        self.module_dependency_resolver = module_dependency_resolver
        self.module_name = module_name
        self.module_version = module_version

    def shell_commands(self, requirement):
        command = '%s load %s' % (self.module_dependency_resolver.module_command, self.module_name)
        if self.module_version:
            command = '%s/%s' % self.module_version
        return command

__all__ = [ModuleDependencyResolver]
