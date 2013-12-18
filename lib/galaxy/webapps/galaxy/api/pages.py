"""
API for updating Galaxy Pages
"""
import logging
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import SharableItemSecurityMixin, BaseAPIController, SharableMixin
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.sanitize_html import sanitize_html

log = logging.getLogger( __name__ )


class PagesController( BaseAPIController, SharableItemSecurityMixin, UsesAnnotations, SharableMixin ):

    @expose_api
    def index( self, trans, **kwd ):
        # Dropping deleted, not implemented yet, adding filter by user.
        # TODO: implemented deleted on/off switch.
        # TODO: Also show pages shared with user. (Public pages?)
        r = trans.sa_session.query( trans.app.model.Page ).filter_by( user=trans.user )
        out = []
        for row in r:
            out.append( self.encode_all_ids( trans, row.to_dict(), True) )
        return out

    @expose_api
    def create( self, trans, payload, **kwd ):
        """
        payload keys:
            slug
            title
            content
            annotation
        """
        user = trans.get_user()

        if not payload.get("title", None):
            raise exceptions.ObjectAttributeMissingException( "Page name is required" )
        elif not payload.get("slug", None):
            raise exceptions.ObjectAttributeMissingException( "Page id is required" )
        elif not self._is_valid_slug( payload["slug"] ):
            raise exceptions.ObjectAttributeInvalidException( "Page identifier must consist of only lowercase letters, numbers, and the '-' character" )
        elif trans.sa_session.query( trans.app.model.Page ).filter_by( user=user, slug=payload["slug"], deleted=False ).first():
            raise exceptions.DuplicatedSlugException( "Page slug must be unique" )
        # Create the new stored page
        page = trans.app.model.Page()
        page.title = payload['title']
        page.slug = payload['slug']
        page_annotation = sanitize_html( payload.get("annotation", ""), 'utf-8', 'text/html' )
        self.add_item_annotation( trans.sa_session, trans.get_user(), page, page_annotation )
        page.user = user
        # And the first (empty) page revision
        page_revision = trans.app.model.PageRevision()
        page_revision.title = payload['title']
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = payload.get("content", "")
        # Persist
        session = trans.sa_session
        session.add( page )
        session.flush()

        rval = self.encode_all_ids( trans, page.to_dict(), True )
        return rval

    @expose_api
    def delete( self, trans, id, **kwd ):
        page_id = id

        page = None
        try:
            page = trans.sa_session.query(self.app.model.Page).get(trans.security.decode_id(page_id))
        except Exception:
            pass

        if not page:
            raise exceptions.ObjectNotFound()

        # check to see if user has permissions to selected workflow
        if page.user != trans.user and not trans.user_is_admin():
            raise exceptions.ItemOwnershipException( )

        #Mark a workflow as deleted
        page.deleted = True
        trans.sa_session.flush()
        return ''  # TODO: Figure out what to return on DELETE, document in guidelines!

    @expose_api
    def show( self, trans, id, **kwd ):
        # Deleted not implemented for now, so removed from args.
        page = trans.sa_session.query( trans.app.model.Page ).get( trans.security.decode_id( id ) )

        if page.user != trans.get_user():
            raise exceptions.ItemOwnershipException()

        rval = self.encode_all_ids( trans, page.to_dict(), True )
        rval['content'] = page.latest_revision.content
        return rval
