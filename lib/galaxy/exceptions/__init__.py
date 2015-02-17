"""
Custom exceptions for Galaxy
"""

from galaxy import eggs
eggs.require( "Paste" )

from paste import httpexceptions
from ..exceptions import error_codes


class MessageException( Exception ):
    """
    Exception to make throwing errors from deep in controllers easier.
    """
    # status code to be set when used with API.
    status_code = 400
    # Error code information embedded into API json responses.
    err_code = error_codes.UNKNOWN

    def __init__( self, err_msg=None, type="info", **extra_error_info ):
        self.err_msg = err_msg or self.err_code.default_error_message
        self.type = type
        self.extra_error_info = extra_error_info

    def __str__( self ):
        return self.err_msg


class ItemDeletionException( MessageException ):
    pass


class ObjectInvalid( Exception ):
    """ Accessed object store ID is invalid """
    pass

# Please keep the exceptions ordered by status code


class ActionInputError( MessageException ):
    status_code = 400
    err_code = error_codes.USER_REQUEST_INVALID_PARAMETER

    def __init__( self, err_msg, type="error" ):
        super( ActionInputError, self ).__init__( err_msg, type )


class DuplicatedSlugException( MessageException ):
    status_code = 400
    err_code = error_codes.USER_SLUG_DUPLICATE


class DuplicatedIdentifierException( MessageException ):
    status_code = 400
    err_code = error_codes.USER_IDENTIFIER_DUPLICATE


class ObjectAttributeInvalidException( MessageException ):
    status_code = 400
    err_code = error_codes.USER_OBJECT_ATTRIBUTE_INVALID


class ObjectAttributeMissingException( MessageException ):
    status_code = 400
    err_code = error_codes.USER_OBJECT_ATTRIBUTE_MISSING


class MalformedId( MessageException ):
    status_code = 400
    err_code = error_codes.MALFORMED_ID


class UnknownContentsType( MessageException ):
    status_code = 400
    err_code = error_codes.UNKNOWN_CONTENTS_TYPE


class RequestParameterMissingException( MessageException ):
    status_code = 400
    err_code = error_codes.USER_REQUEST_MISSING_PARAMETER


class ToolMetaParameterException( MessageException ):
    status_code = 400
    err_code = error_codes.USER_TOOL_META_PARAMETER_PROBLEM


class RequestParameterInvalidException( MessageException ):
    status_code = 400
    err_code = error_codes.USER_REQUEST_INVALID_PARAMETER


class AuthenticationFailed( MessageException ):
    status_code = 401
    err_code = error_codes.USER_AUTHENTICATION_FAILED


class AuthenticationRequired( MessageException ):
    status_code = 403
    #TODO: as 401 and send WWW-Authenticate: ???
    err_code = error_codes.USER_NO_API_KEY


class ItemAccessibilityException( MessageException ):
    status_code = 403
    err_code = error_codes.USER_CANNOT_ACCESS_ITEM


class ItemOwnershipException( MessageException ):
    status_code = 403
    err_code = error_codes.USER_DOES_NOT_OWN_ITEM


class ConfigDoesNotAllowException( MessageException ):
    status_code = 403
    err_code = error_codes.CONFIG_DOES_NOT_ALLOW


class InsufficientPermissionsException( MessageException ):
    status_code = 403
    err_code = error_codes.INSUFFICIENT_PERMISSIONS


class AdminRequiredException( MessageException ):
    status_code = 403
    err_code = error_codes.ADMIN_REQUIRED


class ObjectNotFound( MessageException ):
    """ Accessed object was not found """
    status_code = 404
    err_code = error_codes.USER_OBJECT_NOT_FOUND

class DeprecatedMethod( MessageException ):
    """
    Method (or a particular form/arg signature) has been removed and won't be available later
    """
    status_code = 404
    #TODO:?? 410 Gone?
    err_code = error_codes.DEPRECATED_API_CALL


class Conflict( MessageException ):
    status_code = 409
    err_code = error_codes.CONFLICT


class InconsistentDatabase ( MessageException ):
    status_code = 500
    err_code = error_codes.INCONSISTENT_DATABASE


class InternalServerError ( MessageException ):
    status_code = 500
    err_code = error_codes.INTERNAL_SERVER_ERROR


class NotImplemented ( MessageException ):
    status_code = 501
    err_code = error_codes.NOT_IMPLEMENTED
