import threading


class TransProxy( object ):

    def __init__( self ):
        self.__thread_local_trans = threading.local()

    def __getattr__( self, item ):
        return getattr( self.__thread_local_trans.trans, item  )

    def set_thread_trans( self, trans ):
        self.__thread_local_trans.trans = trans
