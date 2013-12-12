from galaxy import web
from galaxy.model import History, LibraryFolder


def api_payload_to_create_params( payload ):
    """
    Cleanup API payload to pass into dataset_collections.
    """
    required_parameters = [ "collection_type", "dataset_identifiers" ]
    missing_parameters = [ p for p in required_parameters if p not in payload ]
    if missing_parameters:
        raise Exception("Missing required parameters %s" % missing_parameters)

    params = dict(
        collection_type=payload.get("collection_type"),
        dataset_identifiers=payload.get("dataset_identifiers"),
        name=payload.get("name", None),
    )

    return params


def dictify_dataset_collection_instance( dataset_colleciton_instance, parent, security, view="element" ):
    dict_value = dataset_colleciton_instance.to_dict( view=view )
    encoded_id = security.encode_id( dataset_colleciton_instance.id )
    if isinstance( parent, History ):
        encoded_history_id = security.encode_id( parent.id )
        dict_value[ 'url' ] = web.url_for( 'history_content', history_id=encoded_history_id, id=encoded_id, )
    elif isinstance( parent, LibraryFolder ):
        encoded_library_id = security.encode_id( parent.library.id )
        encoded_folder_id = security.encode_id( parent.id )
        dict_value[ 'url' ] = web.url_for( 'library_content', library_id=encoded_library_id, id=encoded_id, folder_id=encoded_folder_id )
    if view == "element":
        dict_value[ 'datasets' ] = len( dataset_colleciton_instance.collection.datasets )
    security.encode_dict_ids( dict_value )
    return dict_value
