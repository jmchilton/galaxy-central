"""
Migration script to create a table for page-library association.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
import datetime
log = logging.getLogger( __name__ )
now = datetime.datetime.utcnow

metadata = MetaData()

PageLibraryAssociation_table = Table( "page_library_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ),
    UniqueConstraint( "page_id", "library_id")
    )


def upgrade( migrate_engine ):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create page_library_association table.
    try:
        PageLibraryAssociation_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating page_library_association table failed: %s" % str( e ) )


def downgrade( migrate_engine ):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop page_library_association table.
    try:
        PageLibraryAssociation_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping page_library_association table failed: %s" % str( e ) )
