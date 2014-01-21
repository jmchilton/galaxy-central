from .registry import DatasetCollectionTypesRegistry

from galaxy.exceptions import MessageException
from galaxy.exceptions import ItemAccessibilityException
from galaxy.exceptions import ActionInputError
from galaxy.web.base.controller import (
    UsesHistoryDatasetAssociationMixin,
    UsesLibraryMixinItems,
    UsesTagsMixin,
)
from galaxy.util import validation
from galaxy.util.bunch import Bunch

import logging
log = logging.getLogger( __name__ )


class DatasetCollectionsService(
    UsesHistoryDatasetAssociationMixin,
    UsesLibraryMixinItems,
    UsesTagsMixin,
):
    """
    Abstraction for interfacing with dataset collections instance - ideally abstarcts
    out model and plugin details.
    """

    def __init__( self, app ):
        self.type_registry = DatasetCollectionTypesRegistry( app )
        self.model = app.model
        self.security = app.security

    def create(
        self,
        trans,
        parent,  # PRECONDITION: security checks on ability to add to parent occurred during load.
        name,
        collection_type,
        dataset_identifiers=None,
        dataset_instances=None,
        implicit_collection_info=None,
    ):
        """
        """
        if dataset_identifiers is None and dataset_instances is None:
            message = "Create called with invalid parameters, must specify dataset identifiers."
            raise ActionInputError(message)
        if dataset_instances is None:
            dataset_instances = self.__load_dataset_instances( trans, dataset_identifiers )
        type_plugin = self.__type_plugin( collection_type )
        dataset_collection = type_plugin.build_collection( dataset_instances )
        dataset_collection.name = name
        if isinstance( parent, self.model.History ):
            dataset_collection_instance = self.model.HistoryDatasetCollectionAssociation(
                collection=dataset_collection,
            )
            if implicit_collection_info:
                for input_name, input_collection in implicit_collection_info[ "implicit_inputs" ]:
                    dataset_collection_instance.add_implicit_input_collection( input_name, input_collection )
                dataset_collection_instance.implicit_output_name = implicit_collection_info[ "implicit_output_name" ]
            # Handle setting hid
            parent.add_dataset_collection( dataset_collection_instance )
        elif isinstance( parent, self.model.LibraryFolder ):
            dataset_collection_instance = self.model.LibraryDatasetCollectionAssociation(
                collection=dataset_collection,
                folder=parent,
            )
        else:
            message = "Internal logic error - create called with unknown parent type %s" % type( parent )
            raise MessageException( message )

        return self.__persist( dataset_collection_instance )

    def delete( self, trans, instance_type, id ):
        dataset_collection_instance = self.get_dataset_collection_instance( trans, instance_type, id, check_ownership=True )
        dataset_collection_instance.deleted = True
        trans.sa_session.add( dataset_collection_instance )
        trans.sa_session.flush( )

    def update( self, trans, instance_type, id, payload ):
        dataset_collection_instance = self.get_dataset_collection_instance( trans, instance_type, id, check_ownership=True )
        if trans.user == None:
            anon_allowed_payload = {}
            if 'deleted' in payload:
                anon_allowed_payload[ 'deleted' ] = payload[ 'deleted' ]
            if 'visible' in payload:
                anon_allowed_payload[ 'visible' ] = payload[ 'visible' ]
            payload = self._validate_and_parse_update_payload( anon_allowed_payload )
        else:
            payload = self._validate_and_parse_update_payload( payload )
        changed = self._set_from_dict( trans, dataset_collection_instance, payload )
        return changed

    def _set_from_dict( self, trans, dataset_collection_instance, new_data ):
        # Blatantly stolen from UsesHistoryDatasetAssociationMixin.set_hda_from_dict.

        # send what we can down into the model
        changed = dataset_collection_instance.set_from_dict( new_data )
        # the rest (often involving the trans) - do here
        if 'annotation' in new_data.keys() and trans.get_user():
            dataset_collection_instance.add_item_annotation( trans.sa_session, trans.get_user(), dataset_collection_instance.collection, new_data[ 'annotation' ] )
            changed[ 'annotation' ] = new_data[ 'annotation' ]
        if 'tags' in new_data.keys() and trans.get_user():
            self.set_tags_from_list( trans, dataset_collection_instance.collection, new_data[ 'tags' ], user=trans.user )

        if changed.keys():
            trans.sa_session.flush()

        return changed

    def _validate_and_parse_update_payload( self, payload ):
        validated_payload = {}
        for key, val in payload.items():
            if val is None:
                continue
            if key in ( 'name' ):
                val = validation.validate_and_sanitize_basestring( key, val )
                validated_payload[ key ] = val
            if key in ( 'deleted', 'visible' ):
                validated_payload[ key ] = validation.validate_boolean( key, val )
            elif key == 'tags':
                validated_payload[ key ] = validation.validate_and_sanitize_basestring_list( key, val )
        return validated_payload

    def history_dataset_collections(self, history, query):
        return history.dataset_collections

    def __persist( self, dataset_collection_instance ):
        context = self.model.context
        context.add( dataset_collection_instance )
        context.flush()
        return dataset_collection_instance

    def __load_dataset_instances( self, trans, dataset_identifiers ):
        return dict( [ (key, self.__load_dataset_instance( trans, dataset_identifier ) ) for key, dataset_identifier in  dataset_identifiers.iteritems() ] )

    def __load_dataset_instance( self, trans, dataset_identifier ):
        if not isinstance( dataset_identifier, dict ):
            dataset_identifier = dict( src='hda', id=str( dataset_identifier ) )

        # dateset_identifier is dict {src=hda|ldda, id=<encoded_id>}
        src_type = dataset_identifier.get( 'src', 'hda' )
        encoded_id = dataset_identifier.get( 'id', None )
        if not src_type or not encoded_id:
            raise ActionInputError( "Problem decoding dataset identifier %s" % dataset_identifier )

        if src_type == 'hda':
            dataset = self.get_dataset( trans, encoded_id, check_ownership=True )
        elif src_type == 'ldda':
            dataset = self.get_library_dataset_dataset_association( trans, encoded_id )

        return dataset

    def __type_plugin( self, collection_type ):
        return self.type_registry.get( collection_type )

    def match_collections( self, collections ):
        """
        May seem odd to place it here, but planning to grow sophistication and
        get plugin types involved so it will likely make sense in the future.
        """
        collection_info = None
        first = True
        for input_key, hdc in collections.iteritems():
            iteration_element_identifiers = sorted( map( lambda d: d.element_identifier, hdc.collection.datasets ) )
            iteration_collection_type = hdc.collection.collection_type
            if first:
                first = False
                collection_info = Bunch(
                    identifiers=iteration_element_identifiers,
                    type=iteration_collection_type,
                    collections={ input_key: hdc },
                )
            else:
                error_message = None
                if collection_info.type != iteration_collection_type:
                    error_message = "Cannot match collection types."
                if collection_info.identifiers != iteration_element_identifiers:
                    # TODO: This could be more general...
                    error_message = "Cannot match multirun collection identifiers."
                if error_message:
                    raise MessageException(error_message)
                collection_info.collections[input_key] = hdc

        return collection_info

    def get_dataset_collection_instance( self, trans, instance_type, id, **kwds ):
        """
        """
        if instance_type == "history":
            return self.__get_history_collection_instance( trans, id, **kwds )
        elif instance_type == "library":
            return self.__get_library_collection_instance( trans, id, **kwds )

    def __get_history_collection_instance( self, trans, id, check_ownership=False, check_accessible=True ):
        instance_id = int( trans.app.security.decode_id( id ) )
        collection_instance = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( instance_id )
        # TODO: Verify this throws exception...
        self.security_check( trans, collection_instance.history, check_ownership=check_ownership, check_accessible=check_accessible )
        return collection_instance

    def __get_library_collection_instance( self, trans, id, check_ownership=False, check_accessible=True ):
        if check_ownership:
            raise NotImplemented("Functionality (getting library dataset collection with ownership check) unimplemented.")
        instance_id = int( trans.security.decode_id( id ) )
        collection_instance = trans.sa_session.query( trans.app.model.LibraryDatasetCollectionAssociation ).get( instance_id )
        if check_accessible:
            if not trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), collection_instance, trans.user ):
                raise ItemAccessibilityException( "LibraryDatasetCollectionAssociation is not accessible to the current user", type='error' )
        return collection_instance
