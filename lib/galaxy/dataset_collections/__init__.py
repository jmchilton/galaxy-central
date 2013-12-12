from .registry import DatasetCollectionTypesRegistry

from galaxy.exceptions import ItemAccessibilityException
from galaxy.web.base.controller import SharableItemSecurityMixin


class DatasetCollectionsService(object, SharableItemSecurityMixin):
    """
    Abstraction for interfacing with dataset collections - ideally abstarcts
    out model and plugin details.
    """

    def __init__(self, app):
        self.type_registry = DatasetCollectionTypesRegistry(app)
        self.model = app.model

    def create(self, name, collection_type, dataset_identifiers):
        """
        """
        type_plugin = self.__type_plugin( type )
        dataset_instances = self.__load_dataset_instances( dataset_identifiers )
        dataset_collection = type_plugin.build_datasets( dataset_instances )
        dataset_collection.name = name
        self.__persist( dataset_collection )

    def __persist( self, dataset_collection ):
        context = self.model.context
        context.add( dataset_collection )
        context.flush()

    def __load_datasets(self, dataset_identifiers):
        return dict( [ (key, self.__load_dataset( dataset_identifier ) ) for key, dataset_identifier in  dataset_identifiers.iteritems() ] )

    def __type_plugin(self, type):
        return self.type_registry[type]

    # Would love it if the following methods didn't require trans, some
    # narrower definition of current user perhaps.
    # Interface UserContext { get_roles, get_user, user_is_admin }???
    def get_dataset_collection_instance( self, trans, instance_type, id, **kwds ):
        """
        """
        if instance_type == "history":
            return self.__get_history_collection_instance( self, trans, id, **kwds )
        elif instance_type == "library":
            return self.__get_library_collection_instance( self, trans, id, **kwds )

    def __get_history_collection_instance( self, trans, id, check_ownership=False, check_accessible=True ):
        instance_id = int( self.app.security.decode_id( id ) )
        collection_instance = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( instance_id )
        collection_instance = self.security_check( trans, collection_instance.history, check_ownership=check_ownership, check_accessible=check_accessible )
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
