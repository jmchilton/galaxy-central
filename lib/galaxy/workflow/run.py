import uuid

from galaxy import model
from galaxy import exceptions
from galaxy import util

from galaxy.dataset_collections import matching

from galaxy.jobs.actions.post import ActionBox

from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.parameters.basic import DataCollectionToolParameter
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.wrapped import make_dict_copy
from galaxy.tools.execute import execute
from galaxy.util.odict import odict
from galaxy.workflow import modules
from galaxy.workflow.run_request import WorkflowRunConfig
from galaxy.workflow.run_request import workflow_run_config_to_request

import logging
log = logging.getLogger( __name__ )


class DelayedWorkflowEvaluation(Exception):
    pass


def invoke( trans, workflow, workflow_run_config, workflow_invocation=None ):
    """ Run the supplied workflow in the supplied target_history.
    """
    return WorkflowInvoker(
        trans,
        workflow,
        workflow_run_config,
        workflow_invocation=workflow_invocation,
    ).invoke()
    if workflow_invocation:
        # Be sure to update state of workflow_invocation.
        trans.sa_session.flush()


def queue_invoke( trans, workflow, workflow_run_config, request_params ):
    workflow_request = workflow_run_config_to_request( trans, workflow_run_config )
    workflow_invocation = model.WorkflowInvocation()
    workflow_invocation.workflow = workflow
    workflow_invocation.state = model.WorkflowInvocation.states.NEW
    workflow_invocation.scheduler_id = request_params[ "scheduler_id" ]
    workflow_invocation.request = workflow_request

    trans.sa_session.add( workflow_invocation )
    trans.sa_session.flush()

    return workflow_invocation


class WorkflowInvoker( object ):

    def __init__( self, trans, workflow, workflow_run_config, workflow_invocation=None ):
        self.trans = trans
        self.workflow = workflow
        if workflow_invocation is None:
            workflow_invocation = model.WorkflowInvocation()
            workflow_invocation.workflow = self.workflow
            self.workflow_invocation = workflow_invocation
        else:
            self.workflow_invocation = workflow_invocation
        self.target_history = workflow_run_config.target_history
        self.replacement_dict = workflow_run_config.replacement_dict
        self.copy_inputs_to_history = workflow_run_config.copy_inputs_to_history

        param_map = workflow_run_config.param_map
        workflow_injector = ApiWorkflowModuleInjector( trans, param_map )
        self.progress = WorkflowProgress( workflow_injector, self.workflow_invocation, workflow_run_config.inputs )

        # TODO: Attach to actual model object and persist someday...
        self.invocation_uuid = uuid.uuid1().hex

    def invoke( self ):
        workflow_invocation = self.workflow_invocation
        remaining_steps = self.progress.remaining_steps()
        delayed_steps = False
        for step in remaining_steps:
            try:
                jobs = self._invoke_step( step )
                for job in util.listify( jobs ):
                    # Record invocation
                    workflow_invocation_step = model.WorkflowInvocationStep()
                    workflow_invocation_step.workflow_invocation = workflow_invocation
                    workflow_invocation_step.workflow_step = step
                    workflow_invocation_step.job = job
            except DelayedWorkflowEvaluation:
                delayed_steps = True

        if delayed_steps:
            state = model.WorkflowInvocation.states.READY
        else:
            state = model.WorkflowInvocation.states.NEW
        workflow_invocation.state = state

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add( workflow_invocation )

        # Not flushing in here, because web controller may create multiple
        # invocations.
        return self.progress.outputs

    def _invoke_step( self, step ):
        if step.type == 'tool' or step.type is None:
            jobs = self._execute_tool_step( step )
        else:
            jobs = self._execute_input_step( step )

        return jobs

    def _execute_tool_step( self, step ):
        trans = self.trans

        tool = trans.app.toolbox.get_tool( step.tool_id )
        tool_state = step.state

        collections_to_match = self._find_collections_to_match( tool, step )
        # Have implicit collections...
        if collections_to_match.has_collections():
            collection_info = self.trans.app.dataset_collections_service.match_collections( collections_to_match )
        else:
            collection_info = None

        param_combinations = []
        if collection_info:
            iteration_elements_iter = collection_info.slice_collections()
        else:
            iteration_elements_iter = [ None ]

        for iteration_elements in iteration_elements_iter:
            execution_state = tool_state.copy()
            # TODO: Move next step into copy()
            execution_state.inputs = make_dict_copy( execution_state.inputs )

            # Connect up
            def callback( input, value, prefixed_name, prefixed_label ):
                replacement = None
                if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                    if iteration_elements and prefixed_name in iteration_elements:
                        if isinstance( input, DataToolParameter ):
                            # Pull out dataset instance from element.
                            replacement = iteration_elements[ prefixed_name ].dataset_instance
                        else:
                            # If collection - just use element model object.
                            replacement = iteration_elements[ prefixed_name ]
                    else:
                        replacement = self._replacement_for_input( input, prefixed_name, step )
                return replacement
            try:
                # Replace DummyDatasets with historydatasetassociations
                visit_input_values( tool.inputs, execution_state.inputs, callback )
            except KeyError, k:
                message_template = "Error due to input mapping of '%s' in '%s'.  A common cause of this is conditional outputs that cannot be determined until runtime, please review your workflow."
                message = message_template % (tool.name, k.message)
                raise exceptions.MessageException( message )
            param_combinations.append( execution_state.inputs )

        execution_tracker = execute(
            trans=self.trans,
            tool=tool,
            param_combinations=param_combinations,
            history=self.target_history,
            collection_info=collection_info,
            workflow_invocation_uuid=self.invocation_uuid
        )
        if collection_info:
            step_outputs = dict( execution_tracker.created_collections )
            
        else:
            step_outputs = dict( execution_tracker.output_datasets )
        self.progress.set_step_outputs( step, step_outputs )
        jobs = execution_tracker.successful_jobs
        for job in jobs:
            self._handle_post_job_actions( step, job )
        return jobs

    def _find_collections_to_match( self, tool, step ):
        collections_to_match = matching.CollectionsToMatch()

        def callback( input, value, prefixed_name, prefixed_label ):
            is_data_param = isinstance( input, DataToolParameter )
            if is_data_param and not input.multiple:
                data = self._replacement_for_input( input, prefixed_name, step )
                if isinstance( data, model.HistoryDatasetCollectionAssociation ):
                    collections_to_match.add( prefixed_name, data )

            is_data_collection_param = isinstance( input, DataCollectionToolParameter )
            if is_data_collection_param and not input.multiple:
                data = self._replacement_for_input( input, prefixed_name, step )
                history_query = input._history_query( self.trans )
                if history_query.can_map_over( data ):
                    collections_to_match.add( prefixed_name, data, subcollection_type=input.collection_type )

        visit_input_values( tool.inputs, step.state.inputs, callback )
        return collections_to_match

    def _execute_input_step( self, step ):
        trans = self.trans

        job, step_outputs = step.module.execute( trans, step.state )

        # Web controller may set copy_inputs_to_history, API controller always sets
        # inputs.
        if self.copy_inputs_to_history:
            for input_dataset_hda in step_outputs.values():
                content_type = input_dataset_hda.history_content_type
                if content_type == "dataset":
                    new_hda = input_dataset_hda.copy( copy_children=True )
                    self.target_history.add_dataset( new_hda )
                    step_outputs[ 'input_ds_copy' ] = new_hda
                elif content_type == "dataset_collection":
                    new_hdca = input_dataset_hda.copy()
                    self.target_history.add_dataset_collection( new_hdca )
                    step_outputs[ 'input_ds_copy' ] = new_hdca
                else:
                    raise Exception("Unknown history content encountered")
        self.progress.set_outputs_for_input( step, step_outputs )
        return job

    def _handle_post_job_actions( self, step, job ):
        # Create new PJA associations with the created job, to be run on completion.
        # PJA Parameter Replacement (only applies to immediate actions-- rename specifically, for now)
        # Pass along replacement dict with the execution of the PJA so we don't have to modify the object.
        for pja in step.post_job_actions:
            if pja.action_type in ActionBox.immediate_actions:
                ActionBox.execute( self.trans.app, self.trans.sa_session, pja, job, self.replacement_dict )
            else:
                job.add_post_job_action( pja )

    def _replacement_for_input( self, input, prefixed_name, step ):
        """ For given workflow 'step' that has had input_connections_by_name
        populated fetch the actual runtime input for the given tool 'input'.
        """
        replacement = None
        if prefixed_name in step.input_connections_by_name:
            connection = step.input_connections_by_name[ prefixed_name ]
            if input.multiple:
                replacement = [ self.progress.replacement_for_connection( c ) for c in connection ]
                # If replacement is just one dataset collection, replace tool
                # input with dataset collection - tool framework will extract
                # datasets properly.
                if len( replacement ) == 1:
                    if isinstance( replacement[ 0 ], model.HistoryDatasetCollectionAssociation ):
                        replacement = replacement[ 0 ]
            else:
                replacement = self.progress.replacement_for_connection( connection[ 0 ] )
        return replacement


STEP_OUTPUT_DELAYED = object()


class WorkflowProgress( object ):

    def __init__( self, module_injector, workflow_invocation, inputs_by_step_id ):
        self.module_injector = module_injector
        self.outputs = odict()
        self.workflow_invocation = workflow_invocation
        self.inputs_by_step_id = inputs_by_step_id

    def remaining_steps(self):
        steps = self.workflow_invocation.workflow.steps

        # Web controller will populate state on each step before calling
        # invoke but not API controller. More work should be done to further
        # harmonize these methods going forward if possible - if possible
        # moving more web controller logic here.
        state_populated = not steps or hasattr( steps[ 0 ], "state" )

        if not state_populated:
            self._populate_state( )

        remaining_steps = []
        step_invocations_by_id = self.workflow_invocation.step_invocations_by_step_id()
        for step in steps:
            invocation_steps = step_invocations_by_id[ step.id ]
            if invocation_steps:
                self._recover_mapping( step, invocation_steps )
            else:
                remaining_steps.append( step )
        return steps

    def replacement_for_connection( self, connection ):
        step_outputs = self.outputs[ connection.output_step.id ]
        if step_outputs is STEP_OUTPUT_DELAYED:
            raise DelayedWorkflowEvaluation()
        return step_outputs[ connection.output_name ]

    def set_outputs_for_input( self, step, outputs={} ):
        if self.inputs_by_step_id:
            outputs[ 'output' ] = self.inputs_by_step_id[ step.id ]

        self.set_step_outputs( step, outputs )

    def set_step_outputs(self, step, outputs):
        self.outputs[ step.id ] = outputs

    def mark_step_outputs_delayed(self, step):
        self.outputs[ step.id ] = STEP_OUTPUT_DELAYED

    def _recover_mapping( self, step, invocation_steps ):
        if step.type == 'tool' or step.type is None:
            self._recover_tool_step( step, invocation_steps )
        else:
            self._recover_input_step( step )

    def _recover_tool_step( self, step, invocation_steps ):
        # TODO: Handle implicit collections...
        job_0 = invocation_steps[ 0 ].job

        outputs = {}
        for job_output in job_0.output_datasets:
            outputs[ job_output.name ] = job_output.dataset
        self.set_step_outputs( step, outputs )

    def _recover_input_step( self, step, invocation_steps ):
        self.set_outputs_for_input( step )

    def _populate_state( self ):
        for step in self.workflow_invocation.workflow.steps:
            self.module_injector.inject(step)


class ApiWorkflowModuleInjector( modules.WorkflowModuleInjector ):
    """ Modules will already be populated if coming from the web controller
    currently - so this variant of the module injector is only used by the API.
    """

    def __init__( self, trans, param_map ):
        super( ApiWorkflowModuleInjector, self ).__init__( trans )
        self.param_map = param_map

    def inject( self, step ):
        """ Use base injection and then replace API supplied parameters and do
        extra checks required by the workflow API.
        """
        step_errors = super( ApiWorkflowModuleInjector, self ).inject( step )
        if step.type == 'tool' or step.type is None:
            _update_step_parameters( step, self.param_map )
            if step.tool_errors:
                message = "Workflow cannot be run because of validation errors in some steps: %s" % step_errors
                raise exceptions.MessageException( message )
            if step.upgrade_messages:
                message = "Workflow cannot be run because of step upgrade messages: %s" % step.upgrade_messages
                raise exceptions.MessageException( message )
        return step_errors


def _update_step_parameters(step, normalized_param_map):
    param_dict = normalized_param_map.get(step.id, {})
    if param_dict:
        step.state.inputs.update(param_dict)


__all__ = [ invoke, WorkflowRunConfig ]
