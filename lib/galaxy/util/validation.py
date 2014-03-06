""" Module for validation of incoming inputs.

TODO: Refactor BaseController references to similar methods to use this module.
"""
from galaxy.util.sanitize_html import sanitize_html


def validate_and_sanitize_basestring( key, val ):
    if not isinstance( val, basestring ):
        raise ValueError( '%s must be a string or unicode: %s' % ( key, str( type( val ) ) ) )
    return unicode( sanitize_html( val, 'utf-8', 'text/html' ), 'utf-8' )


def validate_and_sanitize_basestring_list( key, val ):
    if not isinstance( val, list ):
        raise ValueError( '%s must be a list: %s' % ( key, str( type( val ) ) ) )
    return [ unicode( sanitize_html( t, 'utf-8', 'text/html' ), 'utf-8' ) for t in val ]


def validate_boolean( key, val ):
    if not isinstance( val, bool ):
        raise ValueError( '%s must be a boolean: %s' % ( key, str( type( val ) ) ) )
    return val
