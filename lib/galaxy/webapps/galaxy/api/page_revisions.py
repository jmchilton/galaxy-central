"""
API for updating Galaxy Pages
"""
import logging
from galaxy.web import _future_expose_api as expose_api
from galaxy import exceptions
from galaxy.web.base.controller import SharableItemSecurityMixin, BaseAPIController, SharableMixin
from galaxy.model.item_attrs import UsesAnnotations

log = logging.getLogger( __name__ )


class PageRevisionsController( BaseAPIController, SharableItemSecurityMixin, UsesAnnotations, SharableMixin ):

    @expose_api
    def index( self, trans, page_id, **kwd ):
        page = self._get_page( trans, page_id )
        self._verify_page_ownership( trans, page )
        out = []
        for page_revision in page.revisions:
            out.append( self.encode_all_ids( trans, page_revision.to_dict(), True) )
        return out

    @expose_api
    def create( self, trans, page_id, payload, **kwd ):
        """
        payload keys:
            page_id
            content
        """
        content = payload.get("content", None)
        if not content:
            raise exceptions.ObjectAttributeMissingException("content undefined or empty")

        page = self._get_page( trans, page_id )
        self._verify_page_ownership( trans, page )

        if 'title' in payload:
            title = payload['title']
        else:
            title = page.title

        page_revision = trans.app.model.PageRevision()
        page_revision.title = title
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = payload.get("content", "")
        # Persist
        session = trans.sa_session
        session.flush()

        return page_revision.to_dict( view="element" )

    def _get_page( self, trans, page_id ):
        page = None
        try:
            page = trans.sa_session.query( trans.app.model.Page ).get( trans.security.decode_id(page_id) )
        except Exception:
            pass
        if not page:
            raise exceptions.ObjectNotFound()
        return page

    def _verify_page_ownership( self, trans, page ):
        if not self.security_check( trans, page, True, True ):
            raise exceptions.ItemOwnershipException()
