from galaxy import model
from galaxy import exceptions
from galaxy import util

from galaxy.jobs.actions.post import ActionBox

from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.parameters.basic import DataCollectionToolParameter
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.wrapped import make_dict_copy
from galaxy.tools.execute import execute
from galaxy.util.odict import odict


def invoke( trans, workflow, target_history, replacement_dict, copy_inputs_to_history=False, ds_map={} ):
    """ Run the supplied workflow in the supplied target_history.
    """
    return WorkflowInvoker(
        trans,
        workflow,
        target_history,
        replacement_dict,
        copy_inputs_to_history=copy_inputs_to_history,
        ds_map=ds_map,
    ).invoke()


class WorkflowInvoker( object ):

    def __init__( self, trans, workflow, target_history, replacement_dict, copy_inputs_to_history, ds_map ):
        self.trans = trans
        self.workflow = workflow
        self.target_history = target_history
        self.replacement_dict = replacement_dict
        self.copy_inputs_to_history = copy_inputs_to_history
        self.ds_map = ds_map

        self.outputs = odict()

    def invoke( self ):
        workflow_invocation = model.WorkflowInvocation()
        workflow_invocation.workflow = self.workflow

        for step in self.workflow.steps:
            jobs = self._invoke_step( step )
            for job in util.listify( jobs ):
                # Record invocation
                workflow_invocation_step = model.WorkflowInvocationStep()
                workflow_invocation_step.workflow_invocation = workflow_invocation
                workflow_invocation_step.workflow_step = step
                workflow_invocation_step.job = job

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add( workflow_invocation )

        # Not flushing in here, because web controller may create multiple
        # invokations.
        return self.outputs

    def _invoke_step( self, step ):
        if step.type == 'tool' or step.type is None:
            jobs = self._execute_tool_step( step )
        else:
            jobs = self._execute_input_step( step )

        return jobs

    def _execute_tool_step( self, step ):
        trans = self.trans
        outputs = self.outputs

        tool = trans.app.toolbox.get_tool( step.tool_id )
        tool_state = step.state

        matched_collections = self._find_matched_collections( tool, step )
        # Have implicit collections...
        if matched_collections:
            collection_info = self.trans.app.dataset_collection_service.match_collections( matched_collections )
        else:
            collection_info = None

        all_states = []
        identifiers = ( [ None ] if not collection_info else collection_info.identifiers )
        for identifier in identifiers:
            execution_state = make_dict_copy( tool_state )

            # Connect up
            def callback( input, value, prefixed_name, prefixed_label ):
                replacement = None
                if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                    if identifier and isinstance( input, DataToolParameter ):
                        # TODO: Introduce some sort of mapping here so this doesn't
                        # have to be exact identifier.
                        replacement = collection_info.collections[ prefixed_name ][ identifier ].dataset_instance
                    else:
                        replacement = self._replacement_for_input( input, prefixed_name, step )
                return replacement
            try:
                # Replace DummyDatasets with historydatasetassociations
                visit_input_values( tool.inputs, execution_state, callback )
            except KeyError, k:
                raise exceptions.MessageException( "Error due to input mapping of '%s' in '%s'.  A common cause of this is conditional outputs that cannot be determined until runtime, please review your workflow." % (tool.name, k.message))
            all_states.append( execution_state )

        execution_tracker = execute(
            trans=self.trans,
            tool=tool,
            param_combinations=all_states,
            history=self.target_history
        )
        if collection_info:
            output_collections = execution_tracker.create_output_collections( self.trans, self.target_history, all_states[ 0 ] )
            outputs[ step.id ] = output_collections
        else:
            outputs[ step.id ] = dict( execution_tracker.output_datasets )

        jobs = execution_tracker.successful_jobs
        for job in jobs:
            self._handle_post_job_actions( step, job )
        return jobs

    def _find_matched_collections( self, tool, step ):
        matched_collections = []

        def callback( input, value, prefixed_name, prefixed_label ):
            if isinstance( input, DataToolParameter ):
                data = self._replacement_for_input( input, prefixed_name, step )
                if isinstance( data, model.HistoryDatasetCollectionAssociation ):
                    matched_collections.append( data )

        return matched_collections

    def _execute_input_step( self, step ):
        trans = self.trans
        outputs = self.outputs

        job, out_data = step.module.execute( trans, step.state )
        outputs[ step.id ] = out_data

        # Web controller may set copy_inputs_to_history, API controller always sets
        # ds_map.
        if self.copy_inputs_to_history:
            for input_dataset_hda in out_data.values():
                new_hda = input_dataset_hda.copy( copy_children=True )
                self.target_history.add_dataset( new_hda )
                outputs[ step.id ][ 'input_ds_copy' ] = new_hda
        if self.ds_map:
            outputs[ step.id ][ 'output' ] = self.ds_map[ str( step.id ) ][ 'hda' ]

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
            outputs = self.outputs
            connection = step.input_connections_by_name[ prefixed_name ]
            if input.multiple:
                replacement = [ outputs[ c.output_step.id ][ c.output_name ] for c in connection ]
            else:
                replacement = outputs[ connection[ 0 ].output_step.id ][ connection[ 0 ].output_name ]
        return replacement

__all__ = [ invoke ]
