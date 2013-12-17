"""
Custom exceptions for Galaxy
"""

from galaxy import eggs
eggs.require( "Paste" )

from paste import httpexceptions
from ..exceptions import error_codes


class MessageException( Exception ):
    """
    Exception to make throwing errors from deep in controllers easier
    """
    def __init__( self, err_msg, type="info" ):
        self.err_msg = err_msg
        self.type = type
    def __str__( self ):
        return self.err_msg

class ItemDeletionException( MessageException ):
    pass

class ItemAccessibilityException( MessageException ):
    status_code = 403
    error_code = error_codes.USER_CANNOT_ACCESS_ITEM
    pass

class ItemOwnershipException( MessageException ):
    status_code = 403
    error_code = error_codes.USER_DOES_NOT_OWN_ITEM
    pass

class ActionInputError( MessageException ):
    def __init__( self, err_msg, type="error" ):
        super( ActionInputError, self ).__init__( err_msg, type )

class ObjectNotFound( Exception ):
    """ Accessed object was not found """
    pass

class ObjectInvalid( Exception ):
    """ Accessed object store ID is invalid """
    pass
