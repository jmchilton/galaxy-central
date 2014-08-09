"""
Galaxy Work request system
"""


from galaxy import model


import logging
log = logging.getLogger( __name__ )

import threading
import datetime

import time


def timenow():
    return int(time.time())


now = datetime.datetime.utcnow


class WorkQueue:
    RETRY_COUNT = 10

    def __init__(self, session):
        self.session = session
        self.rlock = threading.RLock()

    def update_queue(self):
        #clean up reserves that have expired
        with self.rlock:
            self.session.query(
                model.WorkRequestReserve
            ).filter(
                model.WorkRequestReserve.update_time + model.WorkRequestReserve.timeout < timenow()
            ).delete()

    def add_request( self, request ):
        with self.rlock:
            self.session.add( request )
            self.session.flush()
            return request

    def complete_request( self, request ):
        request.state = model.WorkRequest.states.COMPLETE
        self.session.add( request )
        self.session.flush()
        return request

    def get_reserve(self, model_type, reserve_handler_id=None, tags=[]):
        with self.rlock:
            for i in range(self.RETRY_COUNT):
                #find a WorkRequest that does not have a WorkRequestReserve
                query = self.__active_work_query( model_type, model.WorkRequestReserve )
                if reserve_handler_id:
                    query = query.filter( model.WorkRequest.reserve_handler_id == reserve_handler_id )

                # TODO: Filter query on tags...

                cur = query.outerjoin(
                    model.WorkRequestReserve
                ).filter(
                    model.WorkRequestReserve.id == None
                ).first()
                if cur is not None:
                    wr = cur[0]
                    #attempt to add a WorkRequestReserve, using the WorkRequest's key as the primary key
                    try:
                        wrr = model.WorkRequestReserve(id=wr.id)
                        self.session.add(wrr)
                        self.session.flush()
                        return wrr
                    except Exception:
                        #if the reserve has been created by another process before we could claim it here
                        #the identity key duplication will throw an error, so we go to the next retry cycle
                        pass
            return None

    def view_waiting(self, model_type, tags=[]):
        self.update_queue()
        with self.rlock:
            q = self.__active_work_query( model_type )
            res = q.outerjoin(
                model.WorkRequestReserve
            ).filter(
                model.WorkRequestReserve.id == None
            ).all()
            return res

    def view_active(self, model_type, tags=[]):
        self.update_queue()
        with self.rlock:
            q = self.__active_work_query( model_type )
            res = q.join(model.WorkRequestReserve).all()
            return res

    def __active_work_query( self, *models ):
        return self.session.query(
            *models
        ).filter(
            model.WorkRequest.state == model.WorkRequest.states.ACTIVE
        )
