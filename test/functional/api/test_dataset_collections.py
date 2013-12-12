from base import api
import json
from .helpers import DatasetPopulator


class DatasetCollectionPopulator( object ):

    def __init__( self, galaxy_interactor ):
        self.galaxy_interactor = galaxy_interactor
        self.dataset_populator = DatasetPopulator( galaxy_interactor )

    def create_pair_payload( self, history_id, **kwds ):

        if "dataset_identifiers" not in kwds:
            kwds[ "dataset_identifiers" ] = json.dumps( self.pair_identifiers( history_id ) )

        payload = dict(
            history_id=history_id,
            collection_type="paired",
            **kwds
        )
        return payload

    def pair_identifiers( self, history_id ):
        hda1 = self.dataset_populator.new_dataset( history_id )
        hda2 = self.dataset_populator.new_dataset( history_id )
        dataset_identifiers = dict(
            left=dict( src="hda", id=hda1[ "id" ] ),
            right=dict( src="hda", id=hda2[ "id" ] ),
        )
        return dataset_identifiers

    def list_identifiers( self, history_id ):
        hda1 = self.dataset_populator.new_dataset( history_id )
        hda2 = self.dataset_populator.new_dataset( history_id )
        hda3 = self.dataset_populator.new_dataset( history_id )

        dataset_identifiers = dict(
            data1=dict( src="hda", id=hda1[ "id" ] ),
            data2=dict( src="hda", id=hda2[ "id" ] ),
            data3=dict( src="hda", id=hda3[ "id" ] ),
        )
        return dataset_identifiers


class DatasetCollectionApiTestCase( api.ApiTestCase ):

    def setUp( self ):
        super( DatasetCollectionApiTestCase, self ).setUp()
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )
        self.dataset_collection_populator = DatasetCollectionPopulator( self.galaxy_interactor )
        self.history_id = self.dataset_populator.new_history()

    def test_create_pair_from_history( self ):
        payload = self.dataset_collection_populator.create_pair_payload(
            self.history_id,
            instance_type="history",
        )
        create_response = self._post( "dataset_collections", payload )
        dataset_collection = self._check_create_response( create_response )
        returned_datasets = dataset_collection[ "datasets" ]
        assert len( returned_datasets ) == 2

    def test_create_list_from_history( self ):
        dataset_identifiers = self.dataset_collection_populator.list_identifiers( self.history_id )

        payload = dict(
            instance_type="history",
            history_id=self.history_id,
            dataset_identifiers=json.dumps(dataset_identifiers),
            collection_type="list",
        )

        create_response = self._post( "dataset_collections", payload )
        dataset_collection = self._check_create_response( create_response )
        returned_datasets = dataset_collection[ "datasets" ]
        assert len( returned_datasets ) == 3

    def test_hda_security( self ):
        dataset_identifiers = self.dataset_collection_populator.pair_identifiers( self.history_id )

        with self._different_user( ):
            history_id = self.dataset_populator.new_history()
            payload = dict(
                instance_type="history",
                history_id=history_id,
                dataset_identifiers=json.dumps(dataset_identifiers),
                collection_type="paired",
            )

            create_response = self._post( "dataset_collections", payload )
            self._assert_status_code_is( create_response, 400 )  # TODO: Really should be 403, but would change a lot?

    def _check_create_response( self, create_response ):
        self._assert_status_code_is( create_response, 200 )
        dataset_collection = create_response.json()
        self._assert_has_keys( dataset_collection, "datasets", "url", "name", "collection_type" )
        return dataset_collection
