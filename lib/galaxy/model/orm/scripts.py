"""
Code to support database helper scripts (create_db.py, manage_db.py, etc...).
"""
import logging
import os.path
import sys
from ConfigParser import SafeConfigParser

from galaxy import eggs  # Needed?

eggs.require( "decorator" )
eggs.require( "Tempita" )
eggs.require( "SQLAlchemy" )
eggs.require( "sqlalchemy_migrate" )

from galaxy.model.orm import dialect_to_egg

import pkg_resources

log = logging.getLogger( __name__ )


def get_config( argv, cwd=None ):
    """
    Read sys.argv and parse out repository of migrations and database url.

    >>> from tempfile import mkdtemp
    >>> config_dir = mkdtemp()
    >>> def write_ini(path, property, value):
    ...     p = SafeConfigParser()
    ...     p.add_section('app:main')
    ...     p.set('app:main', property, value)
    ...     with open(os.path.join(config_dir, path), 'w') as f: p.write(f)
    >>> write_ini('tool_shed_wsgi.ini', 'database_connection', 'sqlite:///pg/testdb1')
    >>> config = get_config(['manage_db.py', 'tool_shed'], cwd=config_dir)
    >>> config['repo']
    'lib/galaxy/webapps/tool_shed/model/migrate'
    >>> config['db_url']
    'sqlite:///pg/testdb1'
    >>> write_ini('universe_wsgi.ini', 'database_file', 'moo.sqlite')
    >>> db_url, repo = get_config(['manage_db.py'], cwd=config_dir)
    >>> config['db_url']
    'sqlite:///moo.sqlite?isolation_level=IMMEDIATE'
    >>> config['repo']
    'lib/galaxy/model/migrate'
    """
    if argv[-1] in [ 'tool_shed' ]:
        # Need to pop the last arg so the command line args will be correct
        # for sqlalchemy-migrate
        argv.pop()
        config_file = 'tool_shed_wsgi.ini'
        repo = 'lib/galaxy/webapps/tool_shed/model/migrate'
    else:
        # Poor man's optparse
        config_file = 'universe_wsgi.ini'
        if '-c' in argv:
            pos = argv.index( '-c' )
            argv.pop(pos)
            config_file = argv.pop( pos )
        if not os.path.exists( config_file ):
            print "Galaxy config file does not exist (hint: use '-c config.ini' for non-standard locations): %s" % config_file
            sys.exit( 1 )
        repo = 'lib/galaxy/model/migrate'

    if cwd:
        config_file = os.path.join( cwd, config_file )

    cp = SafeConfigParser()
    cp.read( config_file )

    if cp.has_option( "app:main", "database_connection" ):
        db_url = cp.get( "app:main", "database_connection" )
    elif cp.has_option( "app:main", "database_file" ):
        db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % cp.get( "app:main", "database_file" )
    else:
        db_url = "sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE"

    dialect = ( db_url.split( ':', 1 ) )[0]
    try:
        egg = dialect_to_egg[dialect]
        try:
            pkg_resources.require( egg )
            log.debug( "%s egg successfully loaded for %s dialect" % ( egg, dialect ) )
        except:
            # If the module is in the path elsewhere (i.e. non-egg), it'll still load.
            log.warning( "%s egg not found, but an attempt will be made to use %s anyway" % ( egg, dialect ) )
    except KeyError:
        # Let this go, it could possibly work with db's we don't support
        log.error( "database_connection contains an unknown SQLAlchemy database dialect: %s" % dialect )

    return dict(db_url=db_url, repo=repo, config_file=config_file)
