import uuid

from galaxy import model
from galaxy import util

from galaxy.util.odict import odict
from galaxy.workflow import modules
from galaxy.workflow.run_request import WorkflowRunConfig
from galaxy.workflow.run_request import workflow_run_config_to_request

import logging
log = logging.getLogger( __name__ )


# Entry point for direct invoke via controllers. Deprecated to some degree.
def invoke( trans, workflow, workflow_run_config, workflow_invocation=None, populate_state=False ):
    if force_queue( trans, workflow ):
        invocation = queue_invoke( trans, workflow, workflow_run_config, populate_state=populate_state )
        return [], invocation
    else:
        return __invoke( trans, workflow, workflow_run_config, workflow_invocation, populate_state )


# Entry point for core workflow scheduler.
def schedule( trans, workflow, workflow_run_config, workflow_invocation ):
    return __invoke( trans, workflow, workflow_run_config, workflow_invocation )


BASIC_WORKFLOW_STEP_TYPES = [ None, "tool", "data_input", "data_collection_input" ]


def force_queue( trans, workflow ):
    # Default behavior is still to just schedule workflows completley right
    # away. This can be modified here in various ways.
    config = trans.app.config
    force_for_collection = config.force_beta_workflow_scheduled_for_collections
    force_min_steps = config.force_beta_workflow_scheduled_min_steps

    step_count = len( workflow.steps )
    if step_count > force_min_steps:
        log.info("Workflow has many steps %d, backgrounding execution" % step_count)
        return True
    for step in workflow.steps:
        if step.type not in BASIC_WORKFLOW_STEP_TYPES:
            log.info("Found non-basic workflow step type - backgrounding execution")
            # Force all new beta modules types to be use force queueing of
            # workflow.
            return True
        if step.type == "data_collection_input" and force_for_collection:
            log.info("Found collection input step - backgrounding execution")
            return True

    return False


def __invoke( trans, workflow, workflow_run_config, workflow_invocation=None, populate_state=False ):
    """ Run the supplied workflow in the supplied target_history.
    """
    if populate_state:
        modules.populate_module_and_state( trans, workflow, workflow_run_config.param_map )

    invoker = WorkflowInvoker(
        trans,
        workflow,
        workflow_run_config,
        workflow_invocation=workflow_invocation,
    )
    try:
        outputs = invoker.invoke()
    except modules.CancelWorkflowEvaluation:
        if workflow_invocation:
            if workflow_invocation.cancel():
                trans.sa_session.add( workflow_invocation )
        outputs = []
    except Exception:
        log.exception("Failed to execute scheduled workflow.")
        if workflow_invocation:
            # Running workflow invocation in background, just mark
            # persistent workflow invocation as failed.
            workflow_invocation.fail()
            trans.sa_session.add( workflow_invocation )
        else:
            # Running new transient workflow invocation in legacy
            # controller action - propage the exception up.
            raise
        outputs = []

    if workflow_invocation:
        # Be sure to update state of workflow_invocation.
        trans.sa_session.flush()

    return outputs, invoker.workflow_invocation


def queue_invoke( trans, workflow, workflow_run_config, request_params={}, populate_state=True ):
    if populate_state:
        modules.populate_module_and_state( trans, workflow, workflow_run_config.param_map )
    workflow_invocation = workflow_run_config_to_request( trans, workflow_run_config, workflow )
    workflow_invocation.workflow = workflow
    return trans.app.workflow_scheduling_manager.queue(
        workflow_invocation,
        request_params
    )


class WorkflowInvoker( object ):

    def __init__( self, trans, workflow, workflow_run_config, workflow_invocation=None ):
        self.trans = trans
        self.workflow = workflow
        if workflow_invocation is None:
            invocation_uuid = uuid.uuid1()

            workflow_invocation = model.WorkflowInvocation()
            workflow_invocation.workflow = self.workflow

            # In one way or another, following attributes will become persistent
            # so they are available during delayed/revisited workflow scheduling.
            workflow_invocation.uuid = invocation_uuid
            workflow_invocation.history = workflow_run_config.target_history

            self.workflow_invocation = workflow_invocation
        else:
            self.workflow_invocation = workflow_invocation

        self.workflow_invocation.copy_inputs_to_history = workflow_run_config.copy_inputs_to_history
        self.workflow_invocation.replacement_dict = workflow_run_config.replacement_dict

        module_injector = modules.WorkflowModuleInjector( trans )
        self.progress = WorkflowProgress( self.workflow_invocation, workflow_run_config.inputs, module_injector )

    def invoke( self ):
        workflow_invocation = self.workflow_invocation
        remaining_steps = self.progress.remaining_steps()
        delayed_steps = False
        for step in remaining_steps:
            jobs = None
            try:
                self.__check_implicitly_dependent_steps(step)

                jobs = self._invoke_step( step )
                for job in (util.listify( jobs ) or [None]):
                    # Record invocation
                    workflow_invocation_step = model.WorkflowInvocationStep()
                    workflow_invocation_step.workflow_invocation = workflow_invocation
                    workflow_invocation_step.workflow_step = step
                    workflow_invocation_step.job = job
            except modules.DelayedWorkflowEvaluation:
                delayed_steps = True
                self.progress.mark_step_outputs_delayed( step )

        if delayed_steps:
            state = model.WorkflowInvocation.states.READY
        else:
            state = model.WorkflowInvocation.states.SCHEDULED
        workflow_invocation.state = state

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add( workflow_invocation )

        # Not flushing in here, because web controller may create multiple
        # invocations.
        return self.progress.outputs

    def __check_implicitly_dependent_steps( self, step ):
        """ Method will delay the workflow evaluation if implicitly dependent
        steps (steps dependent but not through an input->output way) are not
        yet complete.
        """
        for input_connection in step.input_connections:
            if input_connection.non_data_connection:
                output_id = input_connection.output_step.id
                self.__check_implicitly_dependent_step( output_id )

    def __check_implicitly_dependent_step( self, output_id ):
        step_invocations = self.workflow_invocation.step_invocations_for_step_id( output_id )

        # No steps created yet - have to delay evaluation.
        if not step_invocations:
            raise modules.DelayedWorkflowEvaluation()

        for step_invocation in step_invocations:
            job = step_invocation.job
            if job:
                # At least one job in incomplete.
                if not job.finished:
                    raise modules.DelayedWorkflowEvaluation()

                if job.state != job.states.OK:
                    raise modules.CancelWorkflowEvaluation()

            else:
                # TODO: Handle implicit dependency on stuff like
                # pause steps.
                pass

    def _invoke_step( self, step ):
        jobs = step.module.execute( self.trans, self.progress, self.workflow_invocation, step )
        return jobs

STEP_OUTPUT_DELAYED = object()


class WorkflowProgress( object ):

    def __init__( self, workflow_invocation, inputs_by_step_id, module_injector ):
        self.outputs = odict()
        self.module_injector = module_injector
        self.workflow_invocation = workflow_invocation
        self.inputs_by_step_id = inputs_by_step_id

    def remaining_steps(self):
        # Previously computed and persisted step states.
        step_states = self.workflow_invocation.step_states_by_step_id()
        steps = self.workflow_invocation.workflow.steps
        remaining_steps = []
        step_invocations_by_id = self.workflow_invocation.step_invocations_by_step_id()
        for step in steps:
            if not hasattr( step, 'module' ):
                self.module_injector.inject( step )
                runtime_state = step_states[ step.id ].value
                step.state = step.module.recover_runtime_state( runtime_state )

            invocation_steps = step_invocations_by_id.get( step.id, None )
            if invocation_steps:
                self._recover_mapping( step, invocation_steps )
            else:
                remaining_steps.append( step )
        return remaining_steps

    def replacement_for_tool_input( self, step, input, prefixed_name ):
        """ For given workflow 'step' that has had input_connections_by_name
        populated fetch the actual runtime input for the given tool 'input'.
        """
        replacement = None
        if prefixed_name in step.input_connections_by_name:
            connection = step.input_connections_by_name[ prefixed_name ]
            if input.multiple:
                replacement = [ self.replacement_for_connection( c ) for c in connection ]
                # If replacement is just one dataset collection, replace tool
                # input with dataset collection - tool framework will extract
                # datasets properly.
                if len( replacement ) == 1:
                    if isinstance( replacement[ 0 ], model.HistoryDatasetCollectionAssociation ):
                        replacement = replacement[ 0 ]
            else:
                replacement = self.replacement_for_connection( connection[ 0 ] )
        return replacement

    def replacement_for_connection( self, connection ):
        step_outputs = self.outputs[ connection.output_step.id ]
        if step_outputs is STEP_OUTPUT_DELAYED:
            raise modules.DelayedWorkflowEvaluation()
        return step_outputs[ connection.output_name ]

    def set_outputs_for_input( self, step, outputs={} ):
        if self.inputs_by_step_id:
            outputs[ 'output' ] = self.inputs_by_step_id[ step.id ]

        self.set_step_outputs( step, outputs )

    def set_step_outputs(self, step, outputs):
        self.outputs[ step.id ] = outputs

    def mark_step_outputs_delayed(self, step):
        self.outputs[ step.id ] = STEP_OUTPUT_DELAYED

    def _recover_mapping( self, step, step_invocations ):
        try:
            step.module.recover_mapping( step, step_invocations, self )
        except modules.DelayedWorkflowEvaluation:
            self.mark_step_outputs_delayed( step )

__all__ = [ invoke, WorkflowRunConfig ]
