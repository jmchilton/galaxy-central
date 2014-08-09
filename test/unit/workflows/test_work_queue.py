from galaxy import model
from galaxy import work

from .workflow_support import TestApp


def test_work_reservation_unrestricted():
    work_queue = __work_queue_with_request()
    
    reserve = work_queue.get_reserve( model.WorkflowRequest )
    assert reserve is not None

    empty_reserve = work_queue.get_reserve( model.WorkflowRequest )
    assert empty_reserve is None


def test_work_reservation_by_reserve_handler_id():
    work_queue = __work_queue_with_request()
    
    incorrect_handler_id_reserve = work_queue.get_reserve( model.WorkflowRequest, reserve_handler_id="not test123" )
    assert incorrect_handler_id_reserve is None

    correct_handler_id_reserver = work_queue.get_reserve( model.WorkflowRequest, reserve_handler_id="test123" )
    assert correct_handler_id_reserver is not None


def test_state_handling():
    work_queue = __work_queue_with_request()

    assert len( work_queue.view_waiting( model.WorkflowRequest ) ) == 1
    assert len( work_queue.view_active( model.WorkflowRequest ) ) == 0

    reserve = work_queue.get_reserve( model.WorkflowRequest )
    assert reserve

    assert len( work_queue.view_waiting( model.WorkflowRequest ) ) == 0
    assert len( work_queue.view_active( model.WorkflowRequest ) ) == 1


def __work_queue_with_request( work_request=None ):
    work_queue = __work_queue()

    if work_request is None:
        work_request = model.WorkflowRequest()
        work_request.reserve_handler_id = "test123"

    work_queue.add_request( work_request )
    return work_queue


def __work_queue():
    app = TestApp()
    work_queue = work.WorkQueue( app.model.context )
    return work_queue

