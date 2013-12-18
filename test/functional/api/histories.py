from base import api
# requests.post or something like it if unavailable
from base.interactor import post_request


class HistoriesApiTestCase( api.ApiTestCase ):

    def test_create_history( self ):
        data = dict( name="TestHistory1" )
        create_response = self._post( "histories", data=data ).json()
        self._assert_has_keys( create_response, "name", "id" )
        self.assertEquals( create_response[ "name" ], "TestHistory1" )
        created_id = create_response[ "id" ]

        index_response = self._get( "histories" ).json()
        indexed_history = [ history for history in index_response if history[ "id" ] == created_id ][0]
        self.assertEquals(indexed_history[ "name" ], "TestHistory1")

    def test_create_anonymous_fails( self ):
        data = dict(name="CannotCreate")
        histories_url = self._api_url( "histories" )
        create_response = post_request( url=histories_url, data=data )
        self._assert_status_code_is( create_response, 403 )
