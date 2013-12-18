# TODO: We don't need all of TwillTestCase, strip down to a common super class
# shared by API and Twill test cases.
from .twilltestcase import TwillTestCase

from base.interactor import GalaxyInteractorApi

from .api_util import get_master_api_key
from .api_util import get_user_api_key

from urllib import urlencode


# TODO: Allow these to point at existing Galaxy instances.
class ApiTestCase( TwillTestCase ):

    def setUp( self ):
        super( ApiTestCase, self ).setUp( )
        self.user_api_key = get_user_api_key()
        self.master_api_key = get_master_api_key()
        # TODO: Again, GalaxyInteractorApi does too much,
        # make variant used by test_toolbox a subclass of a
        # a based GalaxyInteractorApi shared between this,
        # the tools test API, and the workflow test API.
        self.galaxy_interactor = GalaxyInteractorApi( self, test_user="user@bx.psu.edu" )

    def _api_url( self, path, params=None, use_key=None ):
        if not params:
            params = {}
        url = "%s/api/%s" % ( self.url, path )
        if use_key:
            params[ "key" ] = self.galaxy_interactor.api_key
        query = urlencode( params )
        if query:
            url = "%s?%s" % ( url, query )
        return url

    def _setup_user( self, email ):
        self.galaxy_interactor.ensure_user_with_email(email)
        users = self._get( "users", admin=True ).json()
        user = [ user for user in users if user["email"] == email ][0]
        return user

    def _get( self, *args, **kwds ):
        # Opps.. should not be breaking abstraction like this.
        return self.galaxy_interactor._get( *args, **kwds )

    def _post( self, *args, **kwds ):
        # Opps.. should not be breaking abstraction like this.
        return self.galaxy_interactor._post( *args, **kwds )

    def _assert_status_code_is( self, response, expected_status_code ):
        response_status_code = response.status_code
        self.assertEquals(expected_status_code, response_status_code, "Request status code was not %d, it was %d. Body was %s" % ( expected_status_code, response_status_code, response.json() ) )

    def _assert_has_keys( self, response, *keys ):
        for key in keys:
            assert key in response, "Response [%s] does not contain key [%s]" % ( response, key )

    def _random_key( self ):  # Used for invalid request testing...
        return "1234567890123456"

    _assert_has_key = _assert_has_keys
