""" This module contains functionality to aid in extracting workflows from
histories.
"""
import collections

from galaxy import exceptions
from galaxy.util.odict import odict
from galaxy import model
from galaxy.tools.parameters.basic import (
    DataToolParameter,
    DrillDownSelectToolParameter,
    SelectToolParameter,
    UnvalidatedValue
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    Repeat
)
from .steps import (
    attach_ordered_steps,
    order_workflow_steps_with_levels
)

WARNING_SOME_DATASETS_NOT_READY = "Some datasets still queued or running were ignored"


def extract_workflow( trans, user, history=None, job_ids=None, dataset_ids=None, dataset_collection_ids=None, workflow_name=None ):
    steps = extract_steps( trans, history=history, job_ids=job_ids, dataset_ids=dataset_ids, dataset_collection_ids=dataset_collection_ids )
    # Workflow to populate
    workflow = model.Workflow()
    workflow.name = workflow_name
    # Order the steps if possible
    attach_ordered_steps( workflow, steps )
    # And let's try to set up some reasonable locations on the canvas
    # (these are pretty arbitrary values)
    levorder = order_workflow_steps_with_levels( steps )
    base_pos = 10
    for i, steps_at_level in enumerate( levorder ):
        for j, index in enumerate( steps_at_level ):
            step = steps[ index ]
            step.position = dict( top=( base_pos + 120 * j ),
                                  left=( base_pos + 220 * i ) )
    # Store it
    stored = model.StoredWorkflow()
    stored.user = user
    stored.name = workflow_name
    workflow.stored_workflow = stored
    stored.latest_workflow = workflow
    trans.sa_session.add( stored )
    trans.sa_session.flush()
    return stored


def extract_steps( trans, history=None, job_ids=None, dataset_ids=None, dataset_collection_ids=None ):
    # Ensure job_ids and dataset_ids are lists (possibly empty)
    if job_ids is None:
        job_ids = []
    elif type( job_ids ) is not list:
        job_ids = [ job_ids ]
    if dataset_ids is None:
        dataset_ids = []
    elif type( dataset_ids ) is not list:
        dataset_ids = [ dataset_ids ]
    if dataset_collection_ids is None:
        dataset_collection_ids = []
    elif type( dataset_collection_ids) is not list:
        dataset_collection_ids = [  dataset_collection_ids ]
    # Convert both sets of ids to integers
    job_ids = [ int( id ) for id in job_ids ]
    dataset_ids = [ int( id ) for id in dataset_ids ]
    dataset_collection_ids = [ int( id ) for id in dataset_collection_ids ]
    # Find each job, for security we (implicately) check that they are
    # associated witha job in the current history.
    jobs, warnings, hid_map, implicit_map_jobs = summarize( trans, include_implicit_mapping=True )
    jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
    steps = []
    steps_by_job_id = {}
    hid_to_output_pair = {}
    # Input dataset steps
    for hid in dataset_ids:
        step = model.WorkflowStep()
        step.type = 'data_input'
        step.tool_inputs = dict( name="Input Dataset" )
        hid_to_output_pair[ hid ] = ( step, 'output' )
        steps.append( step )
    for hid in dataset_collection_ids:
        step = model.WorkflowStep()
        step.type = 'data_collection_input'
        step.tool_inputs = dict( name="Input Dataset Collection" )
        hid_to_output_pair[ hid ] = ( step, 'output' )
        steps.append( step )
    # Tool steps
    for job_id in job_ids:
        assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
        job = jobs_by_id[ job_id ]
        tool_inputs, associations = step_inputs( trans, job )
        step = model.WorkflowStep()
        step.type = 'tool'
        step.tool_id = job.tool_id
        step.tool_inputs = tool_inputs
        # NOTE: We shouldn't need to do two passes here since only
        #       an earlier job can be used as an input to a later
        #       job.
        for other_hid, input_name in associations:
            if job in implicit_map_jobs:
                implicit_collection = implicit_map_jobs[ job ][ 0 ]
                input_collection = implicit_collection.find_implicit_input_collection( input_name )
                if input_collection:
                    other_hid = input_collection.hid
            if other_hid in hid_to_output_pair:
                other_step, other_name = hid_to_output_pair[ other_hid ]
                conn = model.WorkflowStepConnection()
                conn.input_step = step
                conn.input_name = input_name
                # Should always be connected to an earlier step
                conn.output_step = other_step
                conn.output_name = other_name
        steps.append( step )
        steps_by_job_id[ job_id ] = step
        # Store created dataset hids
        for assoc in job.output_datasets:
            hid = assoc.dataset.hid
            if hid in hid_map:
                hid = hid_map[ hid ]
            hid_to_output_pair[ assoc.dataset.hid ] = ( step, assoc.name )
    return steps


class FakeJob( object ):
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """
    def __init__( self, dataset ):
        self.is_fake = True
        self.id = "fake_%s" % dataset.id


class DatasetCollectionCreationJob( object ):

    def __init__( self, dataset_collection ):
        self.is_fake = True
        self.id = "fake_%s" % dataset_collection.id
        self.from_jobs = None
        self.name = "Dataset Collection Creation"
        self.disabled_why = "Dataset collection created in a way not compatible with workflows"

    def set_jobs( self, jobs ):
        assert jobs is not None
        self.from_jobs = jobs


def summarize( trans, history=None, include_implicit_mapping=False  ):
    """ Return mapping of job description to datasets for active items in
    supplied history - needed for building workflow from a history.

    Formerly call get_job_dict in workflow web controller.
    """
    if not history:
        history = trans.get_history()

    # Get the jobs that created the datasets
    warnings = set()
    jobs = odict()
    dataset_jobs = {}
    hid_map = {}
    implicit_map_jobs = {}

    def append_dataset( dataset ):
        # FIXME: Create "Dataset.is_finished"
        if dataset.state in ( 'new', 'running', 'queued' ):
            warnings.add( WARNING_SOME_DATASETS_NOT_READY )
            return

        # TODO: need to likewise find job for dataset collections.
        #if this hda was copied from another, we need to find the job that created the origial hda
        job_hda = dataset
        while job_hda.copied_from_history_dataset_association:
            job_hda = job_hda.copied_from_history_dataset_association

        if not job_hda.creating_job_associations:
            job = FakeJob( dataset )
            jobs[ job ] = [ ( None, dataset ) ]

        for assoc in job_hda.creating_job_associations:
            job = assoc.job
            if job in jobs:
                jobs[ job ].append( ( assoc.name, dataset ) )
            else:
                jobs[ job ] = [ ( assoc.name, dataset ) ]

        dataset_jobs[ dataset ] = job

    def replace_datasets_with_implicit_collections( job, collections ):
        for collection in collections:
            found_job = False
            for hda in collection.collection.dataset_instances:
                hda_job = dataset_jobs[ hda ]
                if job == hda_job:
                    found_job = True
                    break

            if not found_job:
                raise exceptions.MessageException( "Cannot determine collection provenance." )

            found_hda = -1  # Index of original dataset
            job_contents = jobs[ job ]
            for i, name_to_dataset in enumerate( job_contents ):
                if name_to_dataset[ 1 ] == hda:
                    found_hda = i
                    break

            if found_hda == -1:
                raise exceptions.MessageException( "Cannot determine collection provenance." )

            hda_content = job_contents[ found_hda ]
            collection_content = ( hda_content[ 0 ], collection )
            job_contents[ found_hda ] = collection_content
            hid_map[ hda_content[ 1 ].hid ] = collection.hid
        implicit_map_jobs[ job ] = collections

    implicit_collections_dict = collections.defaultdict(list)  # Job -> [Collection]
    implicit_jobs_dict = collections.defaultdict(list)  # Collection -> [ Jobs ]

    for content in history.active_contents:
        if content.history_content_type == "dataset_collection":
            if content.implicit_output_name:
                continue
            job = DatasetCollectionCreationJob( content )
            jobs[ job ] = [ ( None, content ) ]
        else:
            append_dataset( content )

    for content in history.active_contents:
        if content.history_content_type == "dataset_collection":
            if content.implicit_output_name:
                for hda in content.collection.dataset_instances:
                    job = dataset_jobs[ hda ]
                    if not job:
                        raise exceptions.MessageException( "Cannot determine collection provenance." )
                    implicit_collections_dict[ job ].append( content )
                    implicit_jobs_dict[ content ].append( job )

    keep_jobs = []
    drop_jobs = []
    for job in sorted( implicit_collections_dict, key=lambda job: job.id ):
        implicit_collections = implicit_collections_dict[ job ]
        if job in drop_jobs:
            continue
        keep_jobs.append( job )
        first = True
        for collection in implicit_collections:
            for other_job in implicit_jobs_dict[ collection ]:
                if job == other_job:
                    continue
                if first:
                    drop_jobs.append( other_job )
                elif other_job not in drop_jobs:
                    raise exceptions.MessageException( "Cannot determine collection provenance." )

            first = False

    for job in drop_jobs:
        del jobs[ job ]
    for job in keep_jobs:
        replace_datasets_with_implicit_collections( job, implicit_collections_dict[ job ])

    if include_implicit_mapping:
        return jobs, warnings, hid_map, implicit_map_jobs
    else:
        return jobs, warnings


def step_inputs( trans, job ):
    tool = trans.app.toolbox.get_tool( job.tool_id )
    param_values = job.get_param_values( trans.app, ignore_errors=True )  # If a tool was updated and e.g. had a text value changed to an integer, we don't want a traceback here
    associations = __cleanup_param_values( tool.inputs, param_values )
    tool_inputs = tool.params_to_strings( param_values, trans.app )
    return tool_inputs, associations


def __cleanup_param_values( inputs, values ):
    """
    Remove 'Data' values from `param_values`, along with metadata cruft,
    but track the associations.
    """
    associations = []
    # dbkey is pushed in by the framework
    if 'dbkey' in values:
        del values['dbkey']
    root_values = values

    # Recursively clean data inputs and dynamic selects
    def cleanup( prefix, inputs, values ):
        for key, input in inputs.items():
            if isinstance( input, ( SelectToolParameter, DrillDownSelectToolParameter ) ):
                if input.is_dynamic and not isinstance( values[key], UnvalidatedValue ):
                    values[key] = UnvalidatedValue( values[key] )
            if isinstance( input, DataToolParameter ):
                tmp = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                # if not( prefix ):
                if tmp:  # this is false for a non-set optional dataset
                    if not isinstance(tmp, list):
                        associations.append( ( tmp.hid, prefix + key ) )
                    else:
                        associations.extend( [ (t.hid, prefix + key) for t in tmp] )

                # Cleanup the other deprecated crap associated with datasets
                # as well. Worse, for nested datasets all the metadata is
                # being pushed into the root. FIXME: MUST REMOVE SOON
                key = prefix + key + "_"
                for k in root_values.keys():
                    if k.startswith( key ):
                        del root_values[k]
            elif isinstance( input, Repeat ):
                group_values = values[key]
                for i, rep_values in enumerate( group_values ):
                    rep_index = rep_values['__index__']
                    cleanup( "%s%s_%d|" % (prefix, key, rep_index ), input.inputs, group_values[i] )
            elif isinstance( input, Conditional ):
                group_values = values[input.name]
                current_case = group_values['__current_case__']
                cleanup( "%s%s|" % ( prefix, key ), input.cases[current_case].inputs, group_values )
    cleanup( "", inputs, values )
    return associations

__all__ = [ summarize, extract_workflow ]
