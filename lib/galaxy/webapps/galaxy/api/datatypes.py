"""
API operations allowing clients to determine datatype supported by Galaxy.
"""

from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy import exceptions
from galaxy.web.base.controller import BaseAPIController
from galaxy.util import asbool
from galaxy.datatypes.data import Data

import logging
log = logging.getLogger( __name__ )


class DatatypesController( BaseAPIController ):

    @expose_api_anonymous
    def index( self, trans, **kwd ):
        """
        GET /api/datatypes
        Return an object containing upload datatypes.
        """
        datatypes_registry = self._datatypes_registry
        extension_only = asbool( kwd.get( 'extension_only', True ) )
        upload_only = asbool( kwd.get( 'upload_only', True ) )
        try:
            if extension_only:
                if upload_only:
                    return datatypes_registry.upload_file_formats
                else:
                    return [ ext for ext in datatypes_registry.datatypes_by_extension ]
            else:
                rval = []
                for elem in datatypes_registry.datatype_elems:
                    if not asbool(elem.get('display_in_upload')) and upload_only:
                        continue
                    keys = ['extension', 'description', 'description_url']
                    dictionary = {}
                    for key in keys:
                        dictionary[key] = elem.get(key)
                    rval.append(dictionary)
                return rval
        except Exception as exception:
            log.error( 'could not get datatypes: %s', str( exception ), exc_info=True )
            if not isinstance( exception, exceptions.MessageException ):
                raise exceptions.InternalServerError( str( exception ) )
            else:
                raise

    @expose_api_anonymous
    def mapping( self, trans, **kwd ):
        '''
        GET /api/datatypes/mapping
        Return a dictionary of class to class mappings.
        '''
        try:
            ext_to_class_name = dict()
            classes = []
            for k, v in self._datatypes_registry.datatypes_by_extension.iteritems():
                c = v.__class__
                ext_to_class_name[k] = c.__module__ + "." + c.__name__
                classes.append( c )
            class_to_classes = dict()

            def visit_bases( types, cls ):
                for base in cls.__bases__:
                    if issubclass( base, Data ):
                        types.add( base.__module__ + "." + base.__name__ )
                    visit_bases( types, base )
            for c in classes:
                n = c.__module__ + "." + c.__name__
                types = set( [ n ] )
                visit_bases( types, c )
                class_to_classes[ n ] = dict( ( t, True ) for t in types )
            return dict( ext_to_class_name=ext_to_class_name, class_to_classes=class_to_classes )

        except Exception as exception:
            log.error( 'could not get datatype mapping: %s', str( exception ), exc_info=True )
            if not isinstance( exception, exceptions.MessageException ):
                raise exceptions.InternalServerError( str( exception ) )
            else:
                raise

    @expose_api_anonymous
    def sniffers( self, trans, **kwd ):
        '''
        GET /api/datatypes/sniffers
        Return a list of sniffers.
        '''
        try:
            rval = []
            for sniffer_elem in self._datatypes_registry.sniffer_elems:
                datatype = sniffer_elem.get( 'type' )
                if datatype is not None:
                    rval.append( datatype )
            return rval
        except Exception as exception:
            log.error( 'could not get datatypes: %s', str( exception ), exc_info=True )
            if not isinstance( exception, exceptions.MessageException ):
                raise exceptions.InternalServerError( str( exception ) )
            else:
                raise

    @expose_api_anonymous
    def converters( self, trans, **kwd ):
        converters = []
        for (source_type, targets) in self._datatypes_registry.datatype_converters.iteritems():
            for target_type in targets:
                converters.append( {
                    'source': source_type,
                    'target': target_type,
                    'tool_id': targets[ target_type ].id,
                } )

        return converters

    @property
    def _datatypes_registry( self ):
        return self.app.datatypes_registry
