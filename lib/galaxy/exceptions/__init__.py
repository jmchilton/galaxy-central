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


# Base class for newer, API enhanced MessageExceptions, should still work
# with the GUI and the API should handle MessageExceptions, but these are just
# better.
class ApiMessageException( MessageException ):
    status_code = 400
    error_code = error_codes.UNKNOWN

    def __init__( self, err_msg=None, type="info" ):
        super( ApiMessageException, self).__init__( err_msg or self.error_code.default_error_message, type )


class ItemAccessibilityException( ApiMessageException ):
    status_code = 403
    error_code = error_codes.USER_CANNOT_ACCESS_ITEM


class ItemOwnershipException( ApiMessageException ):
    status_code = 403
    error_code = error_codes.USER_DOES_NOT_OWN_ITEM


class DuplicatedSlugException( ApiMessageException ):
    status_code = 400
    error_code = error_codes.USER_SLUG_DUPLICATE


class ObjectAttributeInvalidException( ApiMessageException ):
    status_code = 400
    error_code = error_codes.USER_OBJECT_ATTRIBUTE_INVALID


class ObjectAttributeMissingException( ApiMessageException ):
    status_code = 400
    error_code = error_codes.USER_OBJECT_ATTRIBUTE_MISSING



class ActionInputError( MessageException ):
    def __init__( self, err_msg, type="error" ):
        super( ActionInputError, self ).__init__( err_msg, type )


class ObjectNotFound( ApiMessageException ):
    """ Accessed object was not found """
    status_code = 404
    error_code = error_codes.USER_OBJECT_NOT_FOUND

class ObjectInvalid( Exception ):
    """ Accessed object store ID is invalid """
    pass
