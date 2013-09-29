import tempfile
import os.path
from os import makedirs, symlink
import galaxy.tools.deps
from galaxy.util.bunch import Bunch
from contextlib import contextmanager


def touch( fname, data=None ):
    f = open( fname, 'w' )
    if data:
        f.write( data )
    f.close()


def test_tool_dependencies():
    # Setup directories
    base_path = tempfile.mkdtemp()
    # mkdir( base_path )
    for name, version, sub in [ ( "dep1", "1.0", "env.sh" ), ( "dep1", "2.0", "bin" ), ( "dep2", "1.0", None ) ]:
        if sub == "bin":
            p = os.path.join( base_path, name, version, "bin" )
        else:
            p = os.path.join( base_path, name, version )
        try:
            makedirs( p )
        except:
            pass
        if sub == "env.sh":
            touch( os.path.join( p, "env.sh" ) )

    dm = galaxy.tools.deps.DependencyManager( default_base_path=base_path )

    d1_script, d1_path, d1_version = dm.find_dep( "dep1", "1.0" )
    assert d1_script == os.path.join( base_path, 'dep1', '1.0', 'env.sh' )
    assert d1_path == os.path.join( base_path, 'dep1', '1.0' )
    assert d1_version == "1.0"
    d2_script, d2_path, d2_version = dm.find_dep( "dep1", "2.0" )
    assert d2_script == None
    assert d2_path == os.path.join( base_path, 'dep1', '2.0' )
    assert d2_version == "2.0"

    ## Test default versions
    symlink( os.path.join( base_path, 'dep1', '2.0'), os.path.join( base_path, 'dep1', 'default' ) )
    default_script, default_path, default_version = dm.find_dep( "dep1", None )
    assert default_version == "2.0"

    ## Test default will not be fallen back upon by default
    default_script, default_path, default_version = dm.find_dep( "dep1", "2.1" )
    assert default_script == None
    assert default_version == None


TEST_REPO_USER = "devteam"
TEST_REPO_NAME = "bwa"
TEST_REPO_CHANGESET = "12abcd41223da"
TEST_VERSION = "0.5.9"
TEST_REPO = Bunch(
    owner=TEST_REPO_USER,
    name=TEST_REPO_NAME,
    type='set_environment',
    tool_shed_repository=Bunch(
        owner=TEST_REPO_USER,
        name=TEST_REPO_NAME,
        installed_changeset_revision=TEST_REPO_CHANGESET
    )
)


def test_toolshed_set_enviornment():
    # Setup directories
    base_path = tempfile.mkdtemp()
    test_repo = __build_test_repo('set_environment')
    dm = galaxy.tools.deps.DependencyManager( default_base_path=base_path )
    env_settings_dir = os.path.join(base_path, "environment_settings", TEST_REPO_NAME, TEST_REPO_USER, TEST_REPO_NAME, TEST_REPO_CHANGESET)
    os.makedirs(env_settings_dir)
    d1_script, d1_path, d1_version = dm.find_dep( TEST_REPO_NAME, version=None, type='set_environment', installed_tool_dependencies=[test_repo] )
    assert d1_version == None
    assert d1_script == os.path.join(env_settings_dir, "env.sh"), d1_script


def test_toolshed_package():
    # Setup directories
    base_path = tempfile.mkdtemp()
    test_repo = __build_test_repo('package', version=TEST_VERSION)
    dm = galaxy.tools.deps.DependencyManager( default_base_path=base_path )
    package_dir = os.path.join(base_path, TEST_REPO_NAME, TEST_VERSION, TEST_REPO_USER, TEST_REPO_NAME, TEST_REPO_CHANGESET)
    os.makedirs(package_dir)
    touch(os.path.join(package_dir, 'env.sh'))
    d1_script, d1_path, d1_version = dm.find_dep( TEST_REPO_NAME, version=TEST_VERSION, type='package', installed_tool_dependencies=[test_repo] )
    assert d1_version == TEST_VERSION, d1_version
    assert d1_script == os.path.join(package_dir, "env.sh"), d1_script


def __build_test_repo(type, version=None):
    return Bunch(
        owner=TEST_REPO_USER,
        name=TEST_REPO_NAME,
        type=type,
        version=version,
        tool_shed_repository=Bunch(
            owner=TEST_REPO_USER,
            name=TEST_REPO_NAME,
            installed_changeset_revision=TEST_REPO_CHANGESET
        )
    )


def test_parse():
    with __parse_resolvers('''<dependency_resolvers>
  <tool_shed_package />
  <galaxy_package />
</dependency_resolvers>
''') as dependency_resolvers:
        assert 'ToolShed' in dependency_resolvers[0].__class__.__name__
        assert 'Galaxy' in dependency_resolvers[1].__class__.__name__

    with __parse_resolvers('''<dependency_resolvers>
  <galaxy_package />
  <tool_shed_package />
</dependency_resolvers>
''') as dependency_resolvers:
        assert 'Galaxy' in dependency_resolvers[0].__class__.__name__
        assert 'ToolShed' in dependency_resolvers[1].__class__.__name__

    with __parse_resolvers('''<dependency_resolvers>
  <galaxy_package />
  <tool_shed_package />
  <galaxy_package versionless="true" />
</dependency_resolvers>
''') as dependency_resolvers:
        assert not dependency_resolvers[0].versionless
        assert dependency_resolvers[2].versionless


@contextmanager
def __parse_resolvers(xml_content):
    base_path = tempfile.mkdtemp()
    f = tempfile.NamedTemporaryFile()
    f.write(xml_content)
    f.flush()
    dm = galaxy.tools.deps.DependencyManager( default_base_path=base_path, conf_file=f.name )
    yield dm.dependency_resolvers
