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


WorkRequest_table = Table(
    "work_request", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "uuid", UUIDType() ),
    Column( "state", String( 64 ), index=True ),
    Column( "reserve_handler_id", String(255) ),
    Column( "reserve_handler_hints", JSONType, nullable=True ),
    Column( "request_type", String( 64 ), nullable=False ),
)

import time


def int_now():
    return int(time.time())

WorkRequestReserve_table = Table(
    "work_request_reserve", metadata,
    Column( "id", Integer, ForeignKey("work_request.id"), primary_key=True ),
    Column( "reserve_handler_instance_id", JSONType, nullable=True ),
    Column( "reserve_handler_instance_params", JSONType, nullable=True ),
    Column( "state", String( 64 ), index=True ),
    Column( "timeout", Integer, default=60),
    Column( "update_time", Integer, default=int_now, onupdate=int_now )
)


WorkflowRequest_table = Table(
    "workflow_request",
    metadata,
    Column( "work_request_id", Integer, ForeignKey( "work_request.id" ), primary_key=True),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "workflow_invocation", Integer, ForeignKey("workflow_invocation.id") ),
    Column( "workflow_id", Integer, ForeignKey( "workflow.id" )),
)


WorkflowRequestInputParameter_table = Table(
    "workflow_request_input_parameters", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_request_id", Integer, ForeignKey("workflow_request.work_request_id", onupdate="CASCADE", ondelete="CASCADE" )),
    Column( "name", Unicode(255) ),
    Column( "type", Unicode(255) ),
    Column( "value", TEXT ),
)


WorkflowRequestStepParameter_table = Table(
    "workflow_request_step_parameters", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_request_id", Integer, ForeignKey("workflow_request.work_request_id", onupdate="CASCADE", ondelete="CASCADE" )),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id" )),
    Column( "name", Unicode(255) ),
    Column( "value", TEXT ),
)


WorkflowRequestToInputDatasetAssociation_table = Table(
    "workflow_request_to_input_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "name", String(255) ),
    Column( "workflow_request_id", Integer, ForeignKey( "workflow_request.work_request_id" ), index=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id") ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
)


WorkflowRequestToInputDatasetCollectionAssociation_table = Table(
    "workflow_request_to_input_collection_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "name", String(255) ),
    Column( "workflow_request_id", Integer, ForeignKey( "workflow_request.work_request_id" ), index=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id") ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
)


WorkRequestTagAssociation_table = Table(
    "work_request_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "work_request_id", Integer, ForeignKey( "work_request.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True)
)


TABLES = [
    WorkRequest_table,
    WorkRequestReserve_table,
    WorkflowRequest_table,
    WorkflowRequestInputParameter_table,
    WorkflowRequestStepParameter_table,
    WorkflowRequestToInputDatasetAssociation_table,
    WorkflowRequestToInputDatasetCollectionAssociation_table,
    WorkRequestTagAssociation_table,
]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    for table in TABLES:
        __create(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        __drop(table)


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
