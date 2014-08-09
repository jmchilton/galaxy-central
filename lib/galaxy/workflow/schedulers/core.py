""" The class defines the stock Galaxy workflow scheduling plugin - currently
it simply schedules the whole workflow up front when offered.
"""
from ..schedulers import ActiveWorkflowSchedulingPlugin

from galaxy.work import context

from galaxy.workflow import run
from galaxy.workflow import run_request


class CoreWorkflowSchedulingPlugin( ActiveWorkflowSchedulingPlugin ):
    plugin_type = "core"

    def __init__( self, **kwds ):
        pass

    def startup( self, app ):
        self.app = app

    def shutdown( self ):
        pass

    def schedule( self, workflow_request ):
        workflow = workflow_request.workflow
        history = workflow_request.history
        request_context = context.WorkRequestContext(
            app=self.app,
            history=history,
            user=history.user
        )  # trans-like object not tied to a web-thread.
        workflow_run_config = run_request.workflow_request_to_run_config(
            request_context,
            workflow_request
        )
        run.invoke(
            trans=request_context,
            workflow=workflow,
            workflow_run_config=workflow_run_config
        )

__all__ = [ CoreWorkflowSchedulingPlugin ]
