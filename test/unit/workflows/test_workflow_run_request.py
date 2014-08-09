from galaxy import model

from galaxy.workflow import run
from galaxy.workflow import run_request

from .workflow_support import MockTrans


def test_save_and_load_workflow_request():
    trans = MockTrans()
    user = model.User( "user", "pass" )
    history = model.History( user=user )

    model_context = trans.app.model.context

    model_context.add( user )
    model_context.add( history )
    dataset = model.Dataset()

    hda = history.add_dataset( dataset )
    hda_id = hda.id

    workflow_config = run.WorkflowRunConfig(
        target_history=history,
        replacement_dict=dict(sample1="my cool sample"),
        param_map={1: { "foo": "bar"}, 2: {"foo2": "bar2", "foo3": "bar3"} },
        inputs={3: hda },
        copy_inputs_to_history=True,
    )

    workflow_request = run_request.workflow_run_config_to_request(
        trans,
        workflow_config
    )

    assert workflow_request is not None

    model_context.add( workflow_request )
    model_context.flush()

    workflow_request_id = workflow_request.id
    history_id = history.id

    model_context.expunge_all()

    loaded_request = model_context.query( model.WorkflowRequest ).get( workflow_request_id )

    loaded_workflow_config = run_request.workflow_request_to_run_config(
        trans,
        loaded_request,
    )

    assert loaded_workflow_config.target_history.id == history_id
    assert loaded_workflow_config.replacement_dict[ "sample1" ] == "my cool sample"
    print loaded_workflow_config.param_map
    assert loaded_workflow_config.param_map[ 1 ] == { "foo": "bar" }
    assert loaded_workflow_config.param_map[ 2 ] == { "foo2": "bar2", "foo3": "bar3"  }
    assert loaded_workflow_config.copy_inputs_to_history

    assert loaded_workflow_config.inputs[ 3 ].id == hda_id
