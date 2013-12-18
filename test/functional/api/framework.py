# This file doesn't test any API in particular but is meant to functionally
# test the API framework itself.
from base import api


class ApiFrameworkTestCase( api.ApiTestCase ):

    def test_user_cannont_run_as( self ):
        data = dict( name="TestHistory1", run_as="another_user" )
        create_response = self._post( "histories", data=data )
        self.assertEquals(create_response.status_code, 403)

    def test_run_as_invalid_user( self ):
        data = dict( name="TestHistory1", run_as="another_user" )
        create_response = self._post( "histories", data=data, admin=True )
        # Another user does not exist.
        self.assertEquals(create_response.status_code, 400)

    def test_run_as_valid_user( self ):
        run_as_user = self._setup_user( "for_run_as@bx.psu.edu" )
        data = dict( name="TestHistory1", run_as=run_as_user[ "id" ] )
        create_response = self._post( "histories", data=data, admin=True )
        self.assertEquals(create_response.status_code, 200)
