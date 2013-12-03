"""
Creates the initial galaxy database schema using the settings defined in
universe_wsgi.ini.

This script is also wrapped by create_db.sh.

.. note: pass '-c /location/to/your_config.ini' for non-standard ini file
locations.

.. note: if no database_connection is set in universe_wsgi.ini, the default,
sqlite database will be constructed.
    Using the database_file setting in universe_wsgi.ini will create the file
    at the settings location (??)

.. seealso: universe_wsgi.ini, specifically the settings: database_connection
and database file
"""

import sys
import os.path

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy.model.orm.scripts import get_config
from galaxy.model.migrate.check import create_or_verify_database as create_db


def invoke_create():
    config = get_config(sys.argv)
    create_db(config['db_url'], config['config_file'])

if __name__ == "__main__":
    invoke_create()
