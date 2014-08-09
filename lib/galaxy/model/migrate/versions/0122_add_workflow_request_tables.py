"""
Migration script for workflow request tables.
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


WorkflowRequest_table = Table(
    "workflow_request",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "scheduer_id", String(255) ),
)


WorkflowRequestInputParameter_table = Table(
    "workflow_request_input_parameters", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_request_id", Integer, ForeignKey("workflow_request.id", onupdate="CASCADE", ondelete="CASCADE" )),
    Column( "name", Unicode(255) ),
    Column( "type", Unicode(255) ),
    Column( "value", TEXT ),
)


WorkflowRequestStepParameter_table = Table(
    "workflow_request_step_parameters", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_request_id", Integer, ForeignKey("workflow_request.id", onupdate="CASCADE", ondelete="CASCADE" )),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id" )),
    Column( "name", Unicode(255) ),
    Column( "value", TEXT ),
)


WorkflowRequestToInputDatasetAssociation_table = Table(
    "workflow_request_to_input_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "name", String(255) ),
    Column( "workflow_request_id", Integer, ForeignKey( "workflow_request.id" ), index=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id") ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
)


WorkflowRequestToInputDatasetCollectionAssociation_table = Table(
    "workflow_request_to_input_collection_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "name", String(255) ),
    Column( "workflow_request_id", Integer, ForeignKey( "workflow_request.id" ), index=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id") ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
)


TABLES = [
    WorkflowRequest_table,
    WorkflowRequestInputParameter_table,
    WorkflowRequestStepParameter_table,
    WorkflowRequestToInputDatasetAssociation_table,
    WorkflowRequestToInputDatasetCollectionAssociation_table,
]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    for table in TABLES:
        __create(table)

    WorkflowRequest_column = Column( "workflow_request_id", Integer, ForeignKey( "workflow_request.id" ), nullable=True )
    State_column = Column( "state", TrimmedString( 64 ) )
    SchedulerId_column = Column( "scheduler_id", String( 255 ) )
    __add_column( WorkflowRequest_column, "workflow_invocation", metadata )
    __add_column( State_column, "workflow_invocation", metadata )
    __add_column( SchedulerId_column, "workflow_invocation", metadata )

    WorkflowInvocationStepAction_column = Column( "action", JSONType, nullable=True )
    __add_column( WorkflowInvocationStepAction_column, "workflow_invocation_step", metadata )
 

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        __drop(table)

    __drop_column( "workflow_request_id", "workflow_invocation", metadata )
    __drop_column( "state", "workflow_invocation", metadata )
    __drop_column( "scheduler_id", "workflow_invocation", metadata )
    __drop_column( "action", "workflow_invocation_step", metadata )


def __add_column(column, table_name, metadata):
    try:
        table = Table( table_name, metadata, autoload=True )
        column.create( table )
    except Exception as e:
        print str(e)
        log.exception( "Adding column %s column failed." % column)


def __drop_column( column_name, table_name, metadata ):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).drop()
    except Exception as e:
        print str(e)
        log.exception( "Dropping column %s failed." % column_name )


def __create(table):
    try:
        table.create()
    except Exception as e:
        print str(e)
        log.exception("Creating %s table failed: %s" % (table.name, str( e ) ) )


def __drop(table):
    try:
        table.drop()
    except Exception as e:
        print str(e)
        log.exception("Dropping %s table failed: %s" % (table.name, str( e ) ) )
