"""
Migration script to enhance workflow step usability by adding labels and UUIDs.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    StepLabel_column = Column( "label", TrimmedString(255) )
    StepUUID_column = Column( "uuid", UUIDType, nullable=True )
    __add_column( StepLabel_column, "workflow_step", metadata )
    __add_column( StepUUID_column, "workflow_step", metadata )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column( "label", "workflow_step", metadata )
    __drop_column( "uuid", "workflow_step", metadata )


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        column.create( table, **kwds )
    except Exception as e:
        print str(e)
        log.exception( "Adding column %s failed." % column)


def __drop_column( column_name, table_name, metadata ):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).drop()
    except Exception as e:
        print str(e)
        log.exception( "Dropping column %s failed." % column_name )
