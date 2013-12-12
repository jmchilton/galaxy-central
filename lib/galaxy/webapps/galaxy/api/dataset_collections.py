from galaxy import web


from galaxy.web.base.controller import BaseAPIController


class DatasetCollectionsController(
    BaseAPIController
):

    @web.expose_api
    def index( self, trans, **kwd ):
        trans.response.status = 501
        return 'not implemented'

    @web.expose_api
    def create( self, trans, payload ):
        """
        * POST /api/dataset_collections:
            create a new dataset collection

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * collection_type: dataset colltion type to create.
            * name:            the new dataset collections's name

        :rtype:     dict
        :returns:   element view of new dataset collection
        """
        collection_type = payload.get( 'collection_type' )
        dataset_identifiers = payload.get( 'datasets' )
        name = payload.get( 'name', None )

        dataset_collection = self.__service( trans ).create(
            name=name,
            collection_type=collection_type,
            dataset_identifiers=dataset_identifiers,
        )

        return dataset_collection.to_dict( view='element' )

    @web.expose_api
    def show( self, trans, instance_type, id ):
        dataset_collection = self.__service( trans ).get(
            id=id,
            instance_type=instance_type,
        )
        return dataset_collection.to_dict( view='element' )

    def __service( self, trans ):
        service = trans.app.dataset_collections_service
        return service
