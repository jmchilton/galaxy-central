"""
Manager and Serializer for Users.
"""

import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy

from galaxy import model
from galaxy import exceptions
from galaxy import util

from galaxy.managers import base
from galaxy.managers import deletable
from galaxy.managers import api_keys

import logging
log = logging.getLogger( __name__ )


class UserManager( base.ModelManager, deletable.PurgableManagerMixin ):
    model_class = model.User
    foreign_key_name = 'user'

    #TODO: there is quite a bit of functionality around the user (authentication, permissions, quotas, groups/roles)
    #   most of which it may be unneccessary to have here

    #TODO: incorp BaseAPIController.validate_in_users_and_groups
    #TODO: incorp CreatesUsersMixin
    #TODO: incorp CreatesApiKeysMixin
    #TODO: incorporate security/validate_user_input.py
    #TODO: incorporate UsesFormDefinitionsMixin?

    def create( self, trans, **kwargs ):
        """
        Create a new user.
        """
        #TODO: deserialize and validate here
        email = kwargs[ 'email' ]
        username = kwargs[ 'username' ]
        password = kwargs[ 'password' ]
        self._error_on_duplicate_email( trans, email )

        user = model.User( email=email, password=password )
        user.username = username

        if self.app.config.user_activation_on:
            user.active = False
        else:
            # Activation is off, every new user is active by default.
            user.active = True

        self.app.model.context.add( user )
        try:
            self.app.model.context.flush()
            #TODO:?? flush needed for permissions below? If not, make optional
        except sqlalchemy.exc.IntegrityError, db_err:
            raise exceptions.Conflict( db_err.message )

        # can throw an sqlalx.IntegrityError if username not unique

        self.app.security_agent.create_private_user_role( user )
        #TODO: trans
        if trans.webapp.name == 'galaxy':
            # We set default user permissions, before we log in and set the default history permissions
            permissions = self.app.config.new_user_dataset_access_role_default_private
            self.app.security_agent.user_set_default_permissions( user, default_access_private=permissions )
        return user

    def _error_on_duplicate_email( self, trans, email ):
        """
        Check for a duplicate email and raise if found.

        :raises exceptions.Conflict: if any are found
        """
        #TODO: remove this check when unique=True is added to the email column
        if self.by_email( trans, email ) is not None:
            raise exceptions.Conflict( 'Email must be unique', email=email )

    # ---- filters
    def by_email( self, trans, email, filters=None, **kwargs ):
        """
        Find a user by their email.
        """
        filters = self._munge_filters( self.model_class.email == email, filters )
        try:
#TODO: use one_or_none
            return super( UserManager, self ).one( trans, filters=filters, **kwargs )
        except exceptions.ObjectNotFound, not_found:
            return None

    def by_email_like( self, trans, email_with_wildcards, filters=None, order_by=None, **kwargs ):
        """
        Find a user searching with SQL wildcards.
        """
        filters = self._munge_filters( self.model_class.email.like( email_with_wildcards ), filters )
        order_by = order_by or ( model.User.email, )
        return super( UserManager, self ).list( trans, filters=filters, order_by=order_by, **kwargs )

    # ---- admin
    def is_admin( self, trans, user ):
        """
        Return True if this user is an admin.
        """
        admin_emails = self._admin_emails( trans )
        return user and admin_emails and user.email in admin_emails

    def _admin_emails( self, trans ):
        """
        Return a list of admin email addresses from the config file.
        """
        return [ email.strip() for email in self.app.config.get( "admin_users", "" ).split( "," ) ]

    def admins( self, trans, filters=None, **kwargs ):
        """
        Return a list of admin Users.
        """
        filters = self._munge_filters( self.model_class.email.in_( self._admin_emails( trans ) ), filters )
        return super( UserManager, self ).list( trans, filters=filters, **kwargs )

    def error_unless_admin( self, trans, user, msg="Administrators only", **kwargs ):
        """
        Raise an error if `user` is not an admin.

        :raises exceptions.AdminRequiredException: if `user` is not an admin.
        """
        # useful in admin only methods
        if not self.is_admin( trans, user ):
            raise exceptions.AdminRequiredException( msg, **kwargs )
        return user

    # ---- anonymous
    def is_anonymous( self, user ):
        """
        Return True if `user` is anonymous.
        """
        # define here for single point of change and make more readable
        return user is None

    def error_if_anonymous( self, trans, user, msg="Log-in required", **kwargs ):
        """
        Raise an error if `user` is anonymous.
        """
        if user is None:
            #TODO: code is correct (403), but should be named AuthenticationRequired (401 and 403 are flipped)
            raise exceptions.AuthenticationFailed( msg, **kwargs )
        return user

    # ---- current
    def current_user( self, trans ):
        # define here for single point of change and make more readable
        return trans.user

    # ---- api keys
    def create_api_key( self, trans, user ):
        """
        Create and return an API key for `user`.
        """
        #TODO: seems like this should return the model
        return api_keys.ApiKeyManager( self.app ).create_api_key( user )

    #TODO: possibly move to ApiKeyManager
    def valid_api_key( self, trans, user ):
        """
        Return this most recent APIKey for this user or None if none have been created.
        """
        query = ( self.app.model.context.query( model.APIKeys )
                    .filter_by( user=user )
                    .order_by( sqlalchemy.desc( model.APIKeys.create_time ) ) )
        all = query.all()
        for a in all:
            print a.user.username, a.key, a.create_time
        print all
        if len( all ):
            return all[0]
        return None
        #return query.first()

    #TODO: possibly move to ApiKeyManager
    def get_or_create_valid_api_key( self, trans, user ):
        """
        Return this most recent APIKey for this user or create one if none have been
        created.
        """
        existing = self.valid_api_key( trans, user )
        if existing:
            return existing
        return self.create_api_key( self, trans, user )

    # ---- roles
    def private_role( self, trans, user ):
        """
        Return the security agent's private role for `user`.
        """
        #TODO: not sure we need to go through sec agent... it's just the first role of type private
        return self.app.security_agent.get_private_user_role( user )

    def quota( self, trans, user ):
        #TODO: use quota manager
        return self.app.quota_agent.get_percent( user=user )

    def tags_used( self, trans, user, tag_models=None ):
        """
        Return a list of distinct 'user_tname:user_value' strings that the
        given user has used.
        """
        #TODO: simplify and unify with tag manager
        if self.is_anonymous( user ):
            return []

        # get all the taggable model TagAssociations
        if not tag_models:
            tag_models = [ v.tag_assoc_class for v in self.app.tag_handler.item_tag_assoc_info.values() ]
        # create a union of subqueries for each for this user - getting only the tname and user_value
        all_tags_query = None
        for tag_model in tag_models:
            subq = ( self.app.model.context.query( tag_model.user_tname, tag_model.user_value )
                        .filter( tag_model.user == trans.user ) )
            all_tags_query = subq if all_tags_query is None else all_tags_query.union( subq )

        # if nothing init'd the query, bail
        if all_tags_query is None:
            return []

        # boil the tag tuples down into a sorted list of DISTINCT name:val strings
        tags = all_tags_query.distinct().all()
        tags = [( ( name + ':' + val ) if val else name ) for name, val in tags ]
        return sorted( tags )

    def has_requests( self, trans, user ):
        """
        """
        if self.is_anonymous( user ):
            return False
        request_types = self.app.security_agent.get_accessible_request_types( trans, user )
        return ( user.requests or request_types )


class UserSerializer( base.ModelSerializer, deletable.PurgableSerializerMixin ):

    def __init__( self, app ):
        """
        Convert a User and associated data to a dictionary representation.
        """
        super( UserSerializer, self ).__init__( app )
        self.user_manager = UserManager( app )

        self.default_view = 'summary'
        self.add_view( 'summary', [
            'id', 'email', 'username'
        ])
        self.add_view( 'detailed', [
            #'update_time',
            #'create_time',

            'total_disk_usage',
            'nice_total_disk_usage',
            'quota_percent'

            #'deleted',
            #'purged',
            #'active',

            #'preferences',
            # all tags
            'tags_used',
            ## all annotations
            #'annotations'
        ], include_keys_from='summary' )

    def add_serializers( self ):
        super( UserSerializer, self ).add_serializers()
        deletable.PurgableSerializerMixin.add_serializers( self )

        self.serializers.update({
            'id'            : self.serialize_id,
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
            'is_admin'      : lambda t, i, k: self.user_manager.is_admin( t, i ),

            'total_disk_usage' : lambda t, i, k: float( i.total_disk_usage ),
            'quota_percent' : lambda t, i, k: self.user_manager.quota( t, i ),

            'tags_used'     : lambda t, i, k: self.user_manager.tags_used( t, i ),
            #TODO: 'has_requests' is more apt
            'requests'      : lambda t, i, k: self.user_manager.has_requests( t, i )
        })

    def serialize_current_anonymous_user( self, trans, user, keys ):
        # use the current history if any to get usage stats for trans' anonymous user
        #TODO: might be better as sep. Serializer class
        history = trans.history
        if not history:
            raise exceptions.AuthenticationRequired( 'No history for anonymous user usage stats' );

        usage = trans.app.quota_agent.get_usage( trans, history=trans.history )
        percent = trans.app.quota_agent.get_percent( trans=trans, usage=usage )

        # a very small subset of keys available
        values = {
            'id'                    : None,
            'total_disk_usage'      : int( usage ),
            'nice_total_disk_usage' : util.nice_size( usage ),
            'quota_percent'         : percent,
        }
        serialized = {}
        for key in keys:
            if key in values:
                serialized[ key ] = values[ key ]
        return serialized

    def serialize( self, trans, user, keys ):
        """
        Override to return at least some usage info if user is anonymous.
        """
        if self.user_manager.is_anonymous( user ):
            return self.serialize_current_anonymous_user( trans, user, keys )
        return super( UserSerializer, self ).serialize( trans, user, keys )


class AdminUserFilters( base.ModelFilterParser, deletable.PurgableFiltersMixin ):
    model_class = model.User

    def _add_parsers( self ):
        super( AdminUserFilters, self )._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers( self )

        #PRECONDITION: user making the query has been verified as an admin
        self.orm_filter_parsers.update({
            'name'          : { 'op': ( 'eq', 'contains', 'like' ) },
            'email'         : { 'op': ( 'eq', 'contains', 'like' ) },
            'username'      : { 'op': ( 'eq', 'contains', 'like' ) },
            'active'        : { 'op': ( 'eq' ) },
            'disk_usage'    : { 'op': ( 'le', 'ge' ) }
        })

        self.fn_filter_parsers.update({
        })
