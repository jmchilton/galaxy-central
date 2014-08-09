from galaxy.web.framework import ProvidesAppContext


class WorkRequestContext( ProvidesAppContext ):
    """ Stripped down implementation of Galaxy web transaction god object for
    work request handling outside of web threads.

    Things that only need app shouldn't be consuming trans - but there is a
    need for actions potentially tied to users and histories and  hopefully
    this can define that stripped down interface providing access to user and
    history information - but not dealing with web request and response
    objects.
    """

    def __init__( self, app, user=None, history=None ):
        self.app = app
        self.security = app.security
        self.user = user
        self.history = history
