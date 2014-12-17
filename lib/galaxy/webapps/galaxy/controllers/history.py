import logging
from cgi import escape
import urllib

import galaxy.util
from galaxy import model
from galaxy import web
from galaxy import exceptions
from galaxy import managers
from galaxy.datatypes.data import nice_size
from galaxy.model.item_attrs import UsesAnnotations, UsesItemRatings
from galaxy.model.orm import and_, eagerload_all, func
from galaxy import util
from galaxy.util import Params
from galaxy.util.odict import odict
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import error, url_for
from galaxy.web.base.controller import BaseUIController, SharableMixin, UsesHistoryDatasetAssociationMixin, UsesHistoryMixin
from galaxy.web.base.controller import ExportsHistoryMixin
from galaxy.web.base.controller import ImportsHistoryMixin
from galaxy.web.base.controller import ERROR, INFO, SUCCESS, WARNING
from galaxy.web.framework.helpers import grids, iff, time_ago, escape

log = logging.getLogger( __name__ )


class NameColumn( grids.TextColumn ):
    def get_value( self, trans, grid, history ):
        return history.get_display_name()


class HistoryListGrid( grids.Grid ):

    # Custom column types
    class DatasetsByStateColumn( grids.GridColumn, UsesHistoryMixin ):
        def get_value( self, trans, grid, history ):
            state_count_dict = self.get_hda_state_counts( trans, history )

            rval = ''
            for state in ( 'ok', 'running', 'queued', 'error' ):
                count = state_count_dict.get( state, 0 )
                if count:
                    rval += '<div class="count-box state-color-%s">%s</div> ' % (state, count)
            return rval

    class HistoryListNameColumn( NameColumn ):
        def get_link( self, trans, grid, history ):
            link = None
            if not history.deleted:
                link = dict( operation="Switch", id=history.id, use_panels=grid.use_panels, async_compatible=True )
            return link


    class DeletedColumn( grids.DeletedColumn ):
        def get_value( self, trans, grid, history ):
            if history == trans.history:
                return "<strong>current history</strong>"
            if history.purged:
                return "deleted permanently"
            elif history.deleted:
                return "deleted"
            return ""

        def sort( self, trans, query, ascending, column_name=None ):
            if ascending:
                query = query.order_by( self.model_class.table.c.purged.asc(), self.model_class.table.c.update_time.desc() )
            else:
                query = query.order_by( self.model_class.table.c.purged.desc(), self.model_class.table.c.update_time.desc() )
            return query

    # Grid definition
    title = "Saved Histories"
    model_class = model.History
    template='/history/grid.mako'
    default_sort_key = "-update_time"
    columns = [
        HistoryListNameColumn( "Name", key="name", attach_popup=True, filterable="advanced" ),
        DatasetsByStateColumn( "Datasets", key="datasets_by_state", sortable=False, nowrap=True),
        grids.IndividualTagsColumn( "Tags", key="tags", model_tag_association_class=model.HistoryTagAssociation, \
                                    filterable="advanced", grid_name="HistoryListGrid" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", filterable="advanced", sortable=False ),
        grids.GridColumn( "Size on Disk", key="get_disk_size_bytes", format=nice_size, sortable=False ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        DeletedColumn( "Status", key="deleted", filterable="advanced" )
    ]
    columns.append(
        grids.MulticolFilterColumn(
        "search history names and tags",
        cols_to_filter=[ columns[0], columns[2] ],
        key="free-text-search", visible=False, filterable="standard" )
                )
    operations = [
        grids.GridOperation( "Switch", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=True ),
        grids.GridOperation( "View", allow_multiple=False ),
        grids.GridOperation( "Share or Publish", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Copy", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Rename", condition=( lambda item: not item.deleted ), async_compatible=False, inbound=True  ),
        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ), async_compatible=True ),
        grids.GridOperation( "Delete Permanently", condition=( lambda item: not item.purged ), confirm="History contents will be removed from disk, this cannot be undone.  Continue?", async_compatible=True ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted and not item.purged ), async_compatible=True ),
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) ),
    ]
    default_filter = dict( name="All", deleted="False", tags="All", sharing="All" )
    num_rows_per_page = 50
    preserve_state = False
    use_async = True
    use_paging = True
    info_text = "Histories that have been deleted for more than a time period specified by the Galaxy administrator(s) may be permanently deleted."

    def get_current_item( self, trans, **kwargs ):
        return trans.get_history()

    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, importing=False )

class SharedHistoryListGrid( grids.Grid ):

    # Custom column types
    class DatasetsByStateColumn( grids.GridColumn ):
        def get_value( self, trans, grid, history ):
            rval = ''
            for state in ( 'ok', 'running', 'queued', 'error' ):
                total = sum( 1 for d in history.active_datasets if d.state == state )
                if total:
                    rval += '<div class="count-box state-color-%s">%s</div>' % ( state, total )
            return rval

    class SharedByColumn( grids.GridColumn ):
        def get_value( self, trans, grid, history ):
            return history.user.email

    # Grid definition
    title = "Histories shared with you by others"
    model_class = model.History
    default_sort_key = "-update_time"
    default_filter = {}
    columns = [
        grids.GridColumn( "Name", key="name", attach_popup=True ), # link=( lambda item: dict( operation="View", id=item.id ) ), attach_popup=True ),
        DatasetsByStateColumn( "Datasets", sortable=False ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        SharedByColumn( "Shared by", key="user_id" )
    ]
    operations = [
        grids.GridOperation( "View", allow_multiple=False, target="_top" ),
        grids.GridOperation( "Copy" ),
        grids.GridOperation( "Unshare" )
    ]
    standard_filters = []

    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).join( 'users_shared_with' )

    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter( model.HistoryUserShareAssociation.user == trans.user )

class HistoryAllPublishedGrid( grids.Grid ):
    class NameURLColumn( grids.PublicURLColumn, NameColumn ):
        pass

    title = "Published Histories"
    model_class = model.History
    default_sort_key = "update_time"
    default_filter = dict( public_url="All", username="All", tags="All" )
    use_paging = True
    num_rows_per_page = 50
    use_async = True
    columns = [
        NameURLColumn( "Name", key="name", filterable="advanced" ),
        grids.OwnerAnnotationColumn( "Annotation", key="annotation", model_annotation_association_class=model.HistoryAnnotationAssociation, filterable="advanced" ),
        grids.OwnerColumn( "Owner", key="username", model_class=model.User, filterable="advanced" ),
        grids.CommunityRatingColumn( "Community Rating", key="rating" ),
        grids.CommunityTagsColumn( "Community Tags", key="tags", model_tag_association_class=model.HistoryTagAssociation, filterable="advanced", grid_name="PublicHistoryListGrid" ),
        grids.ReverseSortColumn( "Last Updated", key="update_time", format=time_ago )
    ]
    columns.append(
        grids.MulticolFilterColumn(
        "Search name, annotation, owner, and tags",
        cols_to_filter=[ columns[0], columns[1], columns[2], columns[4] ],
        key="free-text-search", visible=False, filterable="standard" )
                )
    operations = []

    def build_initial_query( self, trans, **kwargs ):
        # Join so that searching history.user makes sense.
        return trans.sa_session.query( self.model_class ).join( model.User.table )

    def apply_query_filter( self, trans, query, **kwargs ):
        # A public history is published, has a slug, and is not deleted.
        return query.filter( self.model_class.published == True ).filter( self.model_class.slug != None ).filter( self.model_class.deleted == False )

class HistoryController( BaseUIController, SharableMixin, UsesAnnotations, UsesItemRatings,
                         UsesHistoryMixin, UsesHistoryDatasetAssociationMixin, ExportsHistoryMixin,
                         ImportsHistoryMixin ):

    def __init__( self, app ):
        super( HistoryController, self ).__init__( app )
        self.mgrs = util.bunch.Bunch(
            histories=managers.histories.HistoryManager()
        )

    @web.expose
    def index( self, trans ):
        return ""

    @web.expose
    def list_as_xml( self, trans ):
        """XML history list for functional tests"""
        trans.response.set_content_type( 'text/xml' )
        return trans.fill_template( "/history/list_as_xml.mako" )

    # ......................................................................... lists
    stored_list_grid = HistoryListGrid()
    shared_list_grid = SharedHistoryListGrid()
    published_list_grid = HistoryAllPublishedGrid()

    @web.expose
    def list_published( self, trans, **kwargs ):
        if 'async' in kwargs:
            kwargs[ 'embedded' ] = True
            return self.published_list_grid( trans, **kwargs )

        kwargs[ 'embedded' ] = True
        grid = self.published_list_grid( trans, **kwargs )
        return trans.fill_template( "history/list_published.mako", embedded_grid=grid )


    @web.expose
    @web.require_login( "work with multiple histories" )
    def list( self, trans, **kwargs ):
        """List all available histories"""
        current_history = trans.get_history()
        status = message = None
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "share or publish":
                return self.sharing( trans, **kwargs )
            if operation == "rename" and kwargs.get('id', None): # Don't call rename if no ids
                if 'name' in kwargs:
                    del kwargs['name'] # Remove ajax name param that rename method uses
                return self.rename( trans, **kwargs )
            if operation == "view":
                history = self.get_history( trans, kwargs.get( 'id', None ) )
                if history:
                    return trans.response.send_redirect( url_for( controller='history',
                                                                  action='view',
                                                                  id=kwargs['id'],
                                                                  show_deleted=history.deleted,
                                                                  use_panels=False ) )
                    #return self.view( trans, id=kwargs['id'], show_deleted=history.deleted, use_panels=False )
            if operation == 'copy' and kwargs.get( 'id', None ):
                return self.copy( trans, id=kwargs.get( 'id', None ) )
            history_ids = galaxy.util.listify( kwargs.get( 'id', [] ) )
            # Display no message by default
            status, message = None, None
            refresh_history = False
            # Load the histories and ensure they all belong to the current user
            histories = []
            for history_id in history_ids:
                history = self.get_history( trans, history_id )
                if history:
                    # Ensure history is owned by current user
                    if history.user_id != None and trans.user:
                        assert trans.user.id == history.user_id, "History does not belong to current user"
                    histories.append( history )
                else:
                    log.warn( "Invalid history id '%r' passed to list", history_id )
            if histories:
                if operation == "switch":
                    status, message = self._list_switch( trans, histories )
                    # Take action to update UI to reflect history switch. If
                    # grid is using panels, it is standalone and hence a redirect
                    # to root is needed; if grid is not using panels, it is nested
                    # in the main Galaxy UI and refreshing the history frame
                    # is sufficient.
                    use_panels = kwargs.get('use_panels', False) == 'True'
                    if use_panels:
                        return trans.response.send_redirect( url_for( "/" ) )
                    else:
                        trans.template_context['refresh_frames'] = ['history']
                elif operation in ( "delete", "delete permanently" ):
                    if operation == "delete permanently":
                        status, message = self._list_delete( trans, histories, purge=True )
                    else:
                        status, message = self._list_delete( trans, histories )
                    if current_history in histories:
                        # Deleted the current history, so a new, empty history was
                        # created automatically, and we need to refresh the history frame
                        trans.template_context['refresh_frames'] = ['history']
                elif operation == "undelete":
                    status, message = self._list_undelete( trans, histories )
                elif operation == "unshare":
                    for history in histories:
                        for husa in trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                                    .filter_by( history=history ):
                            trans.sa_session.delete( husa )
                elif operation == "enable import via link":
                    for history in histories:
                        if not history.importable:
                            self._make_item_importable( trans.sa_session, history )
                elif operation == "disable import via link":
                    if history_ids:
                        histories = [ self.get_history( trans, history_id ) for history_id in history_ids ]
                        for history in histories:
                            if history.importable:
                                history.importable = False
                trans.sa_session.flush()
        # Render the list view
        return self.stored_list_grid( trans, status=status, message=message, **kwargs )

    def _list_delete( self, trans, histories, purge=False ):
        """Delete histories"""
        n_deleted = 0
        deleted_current = False
        message_parts = []
        status = SUCCESS
        for history in histories:
            if history.users_shared_with:
                message_parts.append( "History (%s) has been shared with others, unshare it before deleting it.  " % history.name )
                status = ERROR
            else:
                if not history.deleted:
                    # We'll not eliminate any DefaultHistoryPermissions in case we undelete the history later
                    history.deleted = True
                    # If deleting the current history, make a new current.
                    if history == trans.get_history():
                        deleted_current = True
                    trans.log_event( "History (%s) marked as deleted" % history.name )
                    n_deleted += 1
                if purge and trans.app.config.allow_user_dataset_purge:
                    for hda in history.datasets:
                        if trans.user:
                            trans.user.total_disk_usage -= hda.quota_amount( trans.user )
                        hda.purged = True
                        trans.sa_session.add( hda )
                        trans.log_event( "HDA id %s has been purged" % hda.id )
                        trans.sa_session.flush()
                        if hda.dataset.user_can_purge:
                            try:
                                hda.dataset.full_delete()
                                trans.log_event( "Dataset id %s has been purged upon the the purge of HDA id %s" % ( hda.dataset.id, hda.id ) )
                                trans.sa_session.add( hda.dataset )
                            except:
                                log.exception( 'Unable to purge dataset (%s) on purge of hda (%s):' % ( hda.dataset.id, hda.id ) )
                    history.purged = True
                    self.sa_session.add( history )
                    self.sa_session.flush()
        trans.sa_session.flush()
        if n_deleted:
            part = "Deleted %d %s" % ( n_deleted, iff( n_deleted != 1, "histories", "history" ) )
            if purge and trans.app.config.allow_user_dataset_purge:
                part += " and removed %s dataset%s from disk" % ( iff( n_deleted != 1, "their", "its" ), iff( n_deleted != 1, 's', '' ) )
            elif purge:
                part += " but the datasets were not removed from disk because that feature is not enabled in this Galaxy instance"
            message_parts.append( "%s.  " % part )
        if deleted_current:
            #note: this needs to come after commits above or will use an empty history that was deleted above
            trans.get_or_create_default_history()
            message_parts.append( "Your active history was deleted, a new empty history is now active.  " )
            status = INFO
        return ( status, " ".join( message_parts ) )

    def _list_undelete( self, trans, histories ):
        """Undelete histories"""
        n_undeleted = 0
        n_already_purged = 0
        for history in histories:
            if history.purged:
                n_already_purged += 1
            if history.deleted:
                history.deleted = False
                if not history.default_permissions:
                    # For backward compatibility - for a while we were deleting all DefaultHistoryPermissions on
                    # the history when we deleted the history.  We are no longer doing this.
                    # Need to add default DefaultHistoryPermissions in case they were deleted when the history was deleted
                    default_action = trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS
                    private_user_role = trans.app.security_agent.get_private_user_role( history.user )
                    default_permissions = {}
                    default_permissions[ default_action ] = [ private_user_role ]
                    trans.app.security_agent.history_set_default_permissions( history, default_permissions )
                n_undeleted += 1
                trans.log_event( "History (%s) %d marked as undeleted" % ( history.name, history.id ) )
        status = SUCCESS
        message_parts = []
        if n_undeleted:
            message_parts.append( "Undeleted %d %s.  " % ( n_undeleted, iff( n_undeleted != 1, "histories", "history" ) ) )
        if n_already_purged:
            message_parts.append( "%d histories have already been purged and cannot be undeleted." % n_already_purged )
            status = WARNING
        return status, "".join( message_parts )

    def _list_switch( self, trans, histories ):
        """Switch to a new different history"""
        new_history = histories[0]
        galaxy_session = trans.get_galaxy_session()
        try:
            association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                          .filter_by( session_id=galaxy_session.id, history_id=new_history.id ) \
                                          .first()
        except:
            association = None
        new_history.add_galaxy_session( galaxy_session, association=association )
        trans.sa_session.add( new_history )
        trans.sa_session.flush()
        trans.set_history( new_history )
        # No message
        return None, None

    @web.expose
    @web.require_login( "work with shared histories" )
    def list_shared( self, trans, **kwargs ):
        """List histories shared with current user by others"""
        msg = galaxy.util.restore_text( kwargs.get( 'msg', '' ) )
        status = message = None
        if 'operation' in kwargs:
            ids = galaxy.util.listify( kwargs.get( 'id', [] ) )
            operation = kwargs['operation'].lower()
            if operation == "view":
                # Display history.
                history = self.get_history( trans, ids[0], False)
                return self.display_by_username_and_slug( trans, history.user.username, history.slug )
            elif operation == "copy":
                if not ids:
                    message = "Select a history to copy"
                    return self.shared_list_grid( trans, status='error', message=message, **kwargs )
                # When copying shared histories, only copy active datasets
                new_kwargs = { 'copy_choice' : 'active' }
                return self.copy( trans, ids, **new_kwargs )
            elif operation == 'unshare':
                if not ids:
                    message = "Select a history to unshare"
                    return self.shared_list_grid( trans, status='error', message=message, **kwargs )
                # No need to check security, association below won't yield a
                # hit if this user isn't having the history shared with her.
                histories = [ self.get_history( trans, history_id, check_ownership=False ) for history_id in ids ]
                for history in histories:
                    # Current user is the user with which the histories were shared
                    association = trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ).filter_by( user=trans.user, history=history ).one()
                    trans.sa_session.delete( association )
                    trans.sa_session.flush()
                message = "Unshared %d shared histories" % len( ids )
                status = 'done'
        # Render the list view
        return self.shared_list_grid( trans, status=status, message=message, **kwargs )

    # ......................................................................... html
    @web.expose
    def citations( self, trans ):
        # Get history
        history = trans.history
        history_id = trans.security.encode_id( history.id )
        return trans.fill_template( "history/citations.mako", history=history, history_id=history_id )

    @web.expose
    def display_structured( self, trans, id=None ):
        """
        Display a history as a nested structure showing the jobs and workflow
        invocations that created each dataset (if any).
        """
        # Get history
        if id is None:
            id = trans.history.id
        else:
            id = trans.security.decode_id( id )
        # Expunge history from the session to allow us to force a reload
        # with a bunch of eager loaded joins
        trans.sa_session.expunge( trans.history )
        history = trans.sa_session.query( model.History ).options(
                eagerload_all( 'active_datasets.creating_job_associations.job.workflow_invocation_step.workflow_invocation.workflow' ),
                eagerload_all( 'active_datasets.children' )
            ).get( id )
        assert history
        #TODO: formalize to trans.show_error
        assert ( history.user and ( history.user.id == trans.user.id )
            or ( history.id == trans.history.id )
            or ( trans.user_is_admin() ) )
        # Resolve jobs and workflow invocations for the datasets in the history
        # items is filled with items (hdas, jobs, or workflows) that go at the
        # top level
        items = []
        # First go through and group hdas by job, if there is no job they get
        # added directly to items
        jobs = odict()
        for hda in history.active_datasets:
            if hda.visible == False:
                continue
            # Follow "copied from ..." association until we get to the original
            # instance of the dataset
            original_hda = hda
            ## while original_hda.copied_from_history_dataset_association:
            ##     original_hda = original_hda.copied_from_history_dataset_association
            # Check if the job has a creating job, most should, datasets from
            # before jobs were tracked, or from the upload tool before it
            # created a job, may not
            if not original_hda.creating_job_associations:
                items.append( ( hda, None ) )
            # Attach hda to correct job
            # -- there should only be one creating_job_association, so this
            #    loop body should only be hit once
            for assoc in original_hda.creating_job_associations:
                job = assoc.job
                if job in jobs:
                    jobs[ job ].append( ( hda, None ) )
                else:
                    jobs[ job ] = [ ( hda, None ) ]
        # Second, go through the jobs and connect to workflows
        wf_invocations = odict()
        for job, hdas in jobs.iteritems():
            # Job is attached to a workflow step, follow it to the
            # workflow_invocation and group
            if job.workflow_invocation_step:
                wf_invocation = job.workflow_invocation_step.workflow_invocation
                if wf_invocation in wf_invocations:
                    wf_invocations[ wf_invocation ].append( ( job, hdas ) )
                else:
                    wf_invocations[ wf_invocation ] = [ ( job, hdas ) ]
            # Not attached to a workflow, add to items
            else:
                items.append( ( job, hdas ) )
        # Finally, add workflow invocations to items, which should now
        # contain all hdas with some level of grouping
        items.extend( wf_invocations.items() )
        # Sort items by age
        items.sort( key=( lambda x: x[0].create_time ), reverse=True )
        #
        return trans.fill_template( "history/display_structured.mako", items=items, history=history )

    @web.expose
    def structure( self, trans, id=None, **kwargs ):
        """
        """
        if not id:
            id = trans.security.encode_id( trans.history.id )

        history_to_view = self.get_history( trans, id, check_ownership=False, check_accessible=True )
        history_data = self.mgrs.histories._get_history_data( trans, history_to_view )
        history_dictionary = history_data[ 'history' ]
        hda_dictionaries   = history_data[ 'contents' ]

        jobs = ( trans.sa_session.query( trans.app.model.Job )
            .filter( trans.app.model.Job.user == trans.user )
            .filter( trans.app.model.Job.history_id == trans.security.decode_id( id ) ) ).all()
        jobs = map( lambda j: self.encode_all_ids( trans, j.to_dict( 'element' ), True ), jobs )

        tools = {}
        for tool_id in set( map( lambda j: j[ 'tool_id' ], jobs ) ):
            unquoted_id = urllib.unquote_plus( tool_id )
            tool = self.app.toolbox.get_tool( unquoted_id )
            if not tool:
                raise exceptions.ObjectNotFound( "Could not find tool with id '%s'" % tool_id )
                #TODO: some fallback for tool information
            tools[ tool_id ] = tool.to_dict( trans, io_details=True, link_details=True )

        return trans.fill_template( "history/structure.mako", historyId=history_dictionary[ 'id' ],
            history=history_dictionary, hdas=hda_dictionaries, jobs=jobs, tools=tools, **kwargs )

    @web.expose
    def view( self, trans, id=None, show_deleted=False, show_hidden=False, use_panels=True ):
        """
        View a history. If a history is importable, then it is viewable by any user.
        """
        # Get history to view.
        if not id:
            return trans.show_error_message( "You must specify a history you want to view." )

        show_deleted = galaxy.util.string_as_bool( show_deleted )
        show_hidden  = galaxy.util.string_as_bool( show_hidden )
        use_panels   = galaxy.util.string_as_bool( use_panels )

        history_dictionary = {}
        hda_dictionaries   = []
        user_is_owner = False
        try:
            history_to_view = self.get_history( trans, id, check_ownership=False, check_accessible=False )
            if not history_to_view:
                return trans.show_error_message( "The specified history does not exist." )
            if history_to_view.user == trans.user:
                user_is_owner = True

            if( ( history_to_view.user != trans.user )
            # Admin users can view any history
            and ( not trans.user_is_admin() )
            and ( not history_to_view.importable )
            and ( trans.user not in history_to_view.users_shared_with_dot_users ) ):
                return trans.show_error_message( "Either you are not allowed to view this history"
                                               + " or the owner of this history has not made it accessible." )

            # include all datasets: hidden, deleted, and purged
            history_data = self.mgrs.histories._get_history_data( trans, history_to_view )
            history_dictionary = history_data[ 'history' ]
            hda_dictionaries   = history_data[ 'contents' ]

        except Exception, exc:
            user_id = str( trans.user.id ) if trans.user else '(anonymous)'
            log.exception( 'Error bootstrapping history for user %s: %s', user_id, str( exc ) )
            history_dictionary[ 'error' ] = ( 'An error occurred getting the history data from the server. '
                                            + 'Please contact a Galaxy administrator if the problem persists.' )

        return trans.fill_template_mako( "history/view.mako",
            history=history_dictionary, hdas=hda_dictionaries, user_is_owner=user_is_owner,
            show_deleted=show_deleted, show_hidden=show_hidden, use_panels=use_panels )

    @web.expose
    def view_multiple( self, trans, include_deleted_histories=False, order='update' ):
        """
        """
        if not trans.user:
            log_in_url = url_for( controller="user", action="login", use_panels=True )
            log_in_link = "<a href='%s'>log in</a>" % ( log_in_url )
            register_url = url_for( controller="user", action="create", use_panels=True )
            register_link = "<a href='%s'>register</a>" % ( register_url )
            return trans.show_error_message( "You need to %s or %s to use multiple histories"
                                             % ( log_in_link, register_link ), use_panels=True )

        #TODO: allow specifying user_id for admin?
        include_deleted_histories = galaxy.util.string_as_bool( include_deleted_histories )
        order = order if order in ( 'update', 'name', 'size' ) else 'update'

        current_history = trans.get_history()
        current_history_id = trans.security.encode_id( current_history.id ) if current_history else None

        history_dictionaries = []
        for history in self.get_user_histories( trans, user=trans.user, include_deleted=include_deleted_histories ):
            history_dictionary = self.get_history_dict( trans, history )
            history_dictionaries.append( history_dictionary )

        return trans.fill_template_mako( "history/view_multiple.mako",
            current_history_id=current_history_id, histories=history_dictionaries,
            include_deleted_histories=include_deleted_histories, order=order )

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """
        Display history based on a username and slug.
        """
        # Get history.
        session = trans.sa_session
        user = session.query( model.User ).filter_by( username=username ).first()
        history = trans.sa_session.query( model.History ).filter_by( user=user, slug=slug, deleted=False ).first()
        if history is None:
           raise web.httpexceptions.HTTPNotFound()
        # Security check raises error if user cannot access history.
        self.security_check( trans, history, False, True)

        # Get rating data.
        user_item_rating = 0
        if trans.get_user():
            user_item_rating = self.get_user_item_rating( trans.sa_session, trans.get_user(), history )
            if user_item_rating:
                user_item_rating = user_item_rating.rating
            else:
                user_item_rating = 0
        ave_item_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, history )

        # create ownership flag for template, dictify models
        user_is_owner = trans.user == history.user
        history_data = self.mgrs.histories._get_history_data( trans, history )
        history_dict = history_data[ 'history' ]
        hda_dicts = history_data[ 'contents' ]

        history_dict[ 'annotation' ] = self.get_item_annotation_str( trans.sa_session, history.user, history )
        # note: adding original annotation since this is published - get_dict returns user-based annos
        #for hda_dict in hda_dicts:
        #    hda_dict[ 'annotation' ] = hda.annotation
        #    dataset.annotation = self.get_item_annotation_str( trans.sa_session, history.user, dataset )

        return trans.stream_template_mako( "history/display.mako", item=history, item_data=[],
            user_is_owner=user_is_owner, history_dict=history_dict, hda_dicts=hda_dicts,
            user_item_rating = user_item_rating, ave_item_rating=ave_item_rating, num_ratings=num_ratings )

    # ......................................................................... sharing & publishing
    @web.expose
    @web.require_login( "share Galaxy histories" )
    def sharing( self, trans, id=None, histories=[], **kwargs ):
        """ Handle history sharing. """

        # Get session and histories.
        session = trans.sa_session
        # Id values take precedence over histories passed in; last resort is current history.
        if id:
            ids = galaxy.util.listify( id )
            if ids:
                histories = [ self.get_history( trans, history_id ) for history_id in ids ]
        elif not histories:
            histories = [ trans.history ]

        # Do operation on histories.
        for history in histories:
            if 'make_accessible_via_link' in kwargs:
                self._make_item_accessible( trans.sa_session, history )
            elif 'make_accessible_and_publish' in kwargs:
                self._make_item_accessible( trans.sa_session, history )
                history.published = True
            elif 'publish' in kwargs:
                if history.importable:
                    history.published = True
                else:
                    # TODO: report error here.
                    pass
            elif 'disable_link_access' in kwargs:
                history.importable = False
            elif 'unpublish' in kwargs:
                history.published = False
            elif 'disable_link_access_and_unpublish' in kwargs:
                history.importable = history.published = False
            elif 'unshare_user' in kwargs:
                user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( kwargs[ 'unshare_user' ] ) )
                # Look for and delete sharing relation for history-user.
                deleted_sharing_relation = False
                husas = trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ).filter_by( user=user, history=history ).all()
                if husas:
                    deleted_sharing_relation = True
                    for husa in husas:
                        trans.sa_session.delete( husa )
                if not deleted_sharing_relation:
                    history_name = escape( history.name )
                    user_email = escape( user.email )
                    message = "History '%s' does not seem to be shared with user '%s'" % ( history_name, user_email )
                    return trans.fill_template( '/sharing_base.mako', item=history,
                                                message=message, status='error' )


        # Legacy issue: histories made accessible before recent updates may not have a slug. Create slug for any histories that need them.
        for history in histories:
            if history.importable and not history.slug:
                self._make_item_accessible( trans.sa_session, history )

        session.flush()

        return trans.fill_template( "/sharing_base.mako", item=history )

    @web.expose
    @web.require_login( "share histories with other users" )
    def share( self, trans, id=None, email="", **kwd ):
        # If a history contains both datasets that can be shared and others that cannot be shared with the desired user,
        # then the entire history is shared, and the protected datasets will be visible, but inaccessible ( greyed out )
        # in the copyd history
        params = Params( kwd )
        user = trans.get_user()
        # TODO: we have too many error messages floating around in here - we need
        # to incorporate the messaging system used by the libraries that will display
        # a message on any page.
        err_msg = galaxy.util.restore_text( params.get( 'err_msg', '' ) )
        if not email:
            if not id:
                # Default to the current history
                id = trans.security.encode_id( trans.history.id )
            id = galaxy.util.listify( id )
            send_to_err = err_msg
            histories = []
            for history_id in id:
                histories.append( self.get_history( trans, history_id ) )
            return trans.fill_template( "/history/share.mako",
                                        histories=histories,
                                        email=email,
                                        send_to_err=send_to_err )
        histories, send_to_users, send_to_err = self._get_histories_and_users( trans, user, id, email )
        if not send_to_users:
            if not send_to_err:
                send_to_err += "%s is not a valid Galaxy user.  %s" % ( email, err_msg )
            return trans.fill_template( "/history/share.mako",
                                        histories=histories,
                                        email=email,
                                        send_to_err=send_to_err )
        if params.get( 'share_button', False ):
            # The user has not yet made a choice about how to share, so dictionaries will be built for display
            can_change, cannot_change, no_change_needed, unique_no_change_needed, send_to_err = \
                self._populate_restricted( trans, user, histories, send_to_users, None, send_to_err, unique=True )
            send_to_err += err_msg
            if cannot_change and not no_change_needed and not can_change:
                send_to_err = "The histories you are sharing do not contain any datasets that can be accessed by the users with which you are sharing."
                return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )
            if can_change or cannot_change:
                return trans.fill_template( "/history/share.mako",
                                            histories=histories,
                                            email=email,
                                            send_to_err=send_to_err,
                                            can_change=can_change,
                                            cannot_change=cannot_change,
                                            no_change_needed=unique_no_change_needed )
            if no_change_needed:
                return self._share_histories( trans, user, send_to_err, histories=no_change_needed )
            elif not send_to_err:
                # User seems to be sharing an empty history
                send_to_err = "You cannot share an empty history.  "
        return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err )

    @web.expose
    @web.require_login( "share restricted histories with other users" )
    def share_restricted( self, trans, id=None, email="", **kwd ):
        if 'action' in kwd:
            action = kwd[ 'action' ]
        else:
            err_msg = "Select an action.  "
            return trans.response.send_redirect( url_for( controller='history',
                                                          action='share',
                                                          id=id,
                                                          email=email,
                                                          err_msg=err_msg,
                                                          share_button=True ) )
        user = trans.get_user()
        user_roles = user.all_roles()
        histories, send_to_users, send_to_err = self._get_histories_and_users( trans, user, id, email )
        send_to_err = ''
        # The user has made a choice, so dictionaries will be built for sharing
        can_change, cannot_change, no_change_needed, unique_no_change_needed, send_to_err = \
            self._populate_restricted( trans, user, histories, send_to_users, action, send_to_err )
        # Now that we've populated the can_change, cannot_change, and no_change_needed dictionaries,
        # we'll populate the histories_for_sharing dictionary from each of them.
        histories_for_sharing = {}
        if no_change_needed:
            # Don't need to change anything in cannot_change, so populate as is
            histories_for_sharing, send_to_err = \
                self._populate( trans, histories_for_sharing, no_change_needed, send_to_err )
        if cannot_change:
            # Can't change anything in cannot_change, so populate as is
            histories_for_sharing, send_to_err = \
                self._populate( trans, histories_for_sharing, cannot_change, send_to_err )
        # The action here is either 'public' or 'private', so we'll continue to populate the
        # histories_for_sharing dictionary from the can_change dictionary.
        for send_to_user, history_dict in can_change.items():
            for history in history_dict:
                # Make sure the current history has not already been shared with the current send_to_user
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter( and_( trans.app.model.HistoryUserShareAssociation.table.c.user_id == send_to_user.id,
                                                  trans.app.model.HistoryUserShareAssociation.table.c.history_id == history.id ) ) \
                                   .count() > 0:
                    send_to_err += "History (%s) already shared with user (%s)" % ( history.name, send_to_user.email )
                else:
                    # Only deal with datasets that have not been purged
                    for hda in history.activatable_datasets:
                        # If the current dataset is not public, we may need to perform an action on it to
                        # make it accessible by the other user.
                        if not trans.app.security_agent.can_access_dataset( send_to_user.all_roles(), hda.dataset ):
                            # The user with which we are sharing the history does not have access permission on the current dataset
                            if trans.app.security_agent.can_manage_dataset( user_roles, hda.dataset ) and not hda.dataset.library_associations:
                                # The current user has authority to change permissions on the current dataset because
                                # they have permission to manage permissions on the dataset and the dataset is not associated
                                # with a library.
                                if action == "private":
                                    trans.app.security_agent.privately_share_dataset( hda.dataset, users=[ user, send_to_user ] )
                                elif action == "public":
                                    trans.app.security_agent.make_dataset_public( hda.dataset )
                    # Populate histories_for_sharing with the history after performing any requested actions on
                    # its datasets to make them accessible by the other user.
                    if send_to_user not in histories_for_sharing:
                        histories_for_sharing[ send_to_user ] = [ history ]
                    elif history not in histories_for_sharing[ send_to_user ]:
                        histories_for_sharing[ send_to_user ].append( history )
        return self._share_histories( trans, user, send_to_err, histories=histories_for_sharing )

    def _get_histories_and_users( self, trans, user, id, email ):
        if not id:
            # Default to the current history
            id = trans.security.encode_id( trans.history.id )
        id = galaxy.util.listify( id )
        send_to_err = ""
        histories = []
        for history_id in id:
            histories.append( self.get_history( trans, history_id ) )
        send_to_users = []
        for email_address in galaxy.util.listify( email ):
            email_address = email_address.strip()
            if email_address:
                if email_address == user.email:
                    send_to_err += "You cannot send histories to yourself.  "
                else:
                    send_to_user = trans.sa_session.query( trans.app.model.User ) \
                                                   .filter( and_( trans.app.model.User.table.c.email==email_address,
                                                                  trans.app.model.User.table.c.deleted==False ) ) \
                                                   .first()
                    if send_to_user:
                        send_to_users.append( send_to_user )
                    else:
                        send_to_err += "%s is not a valid Galaxy user.  " % email_address
        return histories, send_to_users, send_to_err

    def _populate( self, trans, histories_for_sharing, other, send_to_err ):
        # This method will populate the histories_for_sharing dictionary with the users and
        # histories in other, eliminating histories that have already been shared with the
        # associated user.  No security checking on datasets is performed.
        # If not empty, the histories_for_sharing dictionary looks like:
        # { userA: [ historyX, historyY ], userB: [ historyY ] }
        # other looks like:
        # { userA: {historyX : [hda, hda], historyY : [hda]}, userB: {historyY : [hda]} }
        for send_to_user, history_dict in other.items():
            for history in history_dict:
                # Make sure the current history has not already been shared with the current send_to_user
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter( and_( trans.app.model.HistoryUserShareAssociation.table.c.user_id == send_to_user.id,
                                                  trans.app.model.HistoryUserShareAssociation.table.c.history_id == history.id ) ) \
                                   .count() > 0:
                    send_to_err += "History (%s) already shared with user (%s)" % ( history.name, send_to_user.email )
                else:
                    # Build the dict that will be used for sharing
                    if send_to_user not in histories_for_sharing:
                        histories_for_sharing[ send_to_user ] = [ history ]
                    elif history not in histories_for_sharing[ send_to_user ]:
                        histories_for_sharing[ send_to_user ].append( history )
        return histories_for_sharing, send_to_err

    def _populate_restricted( self, trans, user, histories, send_to_users, action, send_to_err, unique=False ):
        # The user may be attempting to share histories whose datasets cannot all be accessed by other users.
        # If this is the case, the user sharing the histories can:
        # 1) action=='public': choose to make the datasets public if he is permitted to do so
        # 2) action=='private': automatically create a new "sharing role" allowing protected
        #    datasets to be accessed only by the desired users
        # This method will populate the can_change, cannot_change and no_change_needed dictionaries, which
        # are used for either displaying to the user, letting them make 1 of the choices above, or sharing
        # after the user has made a choice.  They will be used for display if 'unique' is True, and will look
        # like: {historyX : [hda, hda], historyY : [hda] }
        # For sharing, they will look like:
        # { userA: {historyX : [hda, hda], historyY : [hda]}, userB: {historyY : [hda]} }
        can_change = {}
        cannot_change = {}
        no_change_needed = {}
        unique_no_change_needed = {}
        user_roles = user.all_roles()
        for history in histories:
            for send_to_user in send_to_users:
                # Make sure the current history has not already been shared with the current send_to_user
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter( and_( trans.app.model.HistoryUserShareAssociation.table.c.user_id == send_to_user.id,
                                                  trans.app.model.HistoryUserShareAssociation.table.c.history_id == history.id ) ) \
                                   .count() > 0:
                    send_to_err += "History (%s) already shared with user (%s)" % ( history.name, send_to_user.email )
                else:
                    # Only deal with datasets that have not been purged
                    for hda in history.activatable_datasets:
                        if trans.app.security_agent.can_access_dataset( send_to_user.all_roles(), hda.dataset ):
                            # The no_change_needed dictionary is a special case.  If both of can_change
                            # and cannot_change are empty, no_change_needed will used for sharing.  Otherwise
                            # unique_no_change_needed will be used for displaying, so we need to populate both.
                            # Build the dictionaries for display, containing unique histories only
                            if history not in unique_no_change_needed:
                                unique_no_change_needed[ history ] = [ hda ]
                            else:
                                unique_no_change_needed[ history ].append( hda )
                            # Build the dictionaries for sharing
                            if send_to_user not in no_change_needed:
                                no_change_needed[ send_to_user ] = {}
                            if history not in no_change_needed[ send_to_user ]:
                                no_change_needed[ send_to_user ][ history ] = [ hda ]
                            else:
                                no_change_needed[ send_to_user ][ history ].append( hda )
                        else:
                            # The user with which we are sharing the history does not have access permission on the current dataset
                            if trans.app.security_agent.can_manage_dataset( user_roles, hda.dataset ):
                                # The current user has authority to change permissions on the current dataset because
                                # they have permission to manage permissions on the dataset.
                                # NOTE: ( gvk )There may be problems if the dataset also has an ldda, but I don't think so
                                # because the user with which we are sharing will not have the "manage permission" permission
                                # on the dataset in their history.  Keep an eye on this though...
                                if unique:
                                    # Build the dictionaries for display, containing unique histories only
                                    if history not in can_change:
                                        can_change[ history ] = [ hda ]
                                    else:
                                        can_change[ history ].append( hda )
                                else:
                                    # Build the dictionaries for sharing
                                    if send_to_user not in can_change:
                                        can_change[ send_to_user ] = {}
                                    if history not in can_change[ send_to_user ]:
                                        can_change[ send_to_user ][ history ] = [ hda ]
                                    else:
                                        can_change[ send_to_user ][ history ].append( hda )
                            else:
                                if action in [ "private", "public" ]:
                                    # The user has made a choice, so 'unique' doesn't apply.  Don't change stuff
                                    # that the user doesn't have permission to change
                                    continue
                                if unique:
                                    # Build the dictionaries for display, containing unique histories only
                                    if history not in cannot_change:
                                        cannot_change[ history ] = [ hda ]
                                    else:
                                        cannot_change[ history ].append( hda )
                                else:
                                    # Build the dictionaries for sharing
                                    if send_to_user not in cannot_change:
                                        cannot_change[ send_to_user ] = {}
                                    if history not in cannot_change[ send_to_user ]:
                                        cannot_change[ send_to_user ][ history ] = [ hda ]
                                    else:
                                        cannot_change[ send_to_user ][ history ].append( hda )
        return can_change, cannot_change, no_change_needed, unique_no_change_needed, send_to_err

    def _share_histories( self, trans, user, send_to_err, histories=None ):
        # histories looks like: { userA: [ historyX, historyY ], userB: [ historyY ] }
        histories = histories or {}
        msg = ""
        sent_to_emails = []
        for send_to_user in histories.keys():
            sent_to_emails.append( send_to_user.email )
        emails = ",".join( e for e in sent_to_emails )
        if not histories:
            send_to_err += "No users have been specified or no histories can be sent without changing permissions or associating a sharing role.  "
        else:
            for send_to_user, send_to_user_histories in histories.items():
                shared_histories = []
                for history in send_to_user_histories:
                    share = trans.app.model.HistoryUserShareAssociation()
                    share.history = history
                    share.user = send_to_user
                    trans.sa_session.add( share )
                    self.create_item_slug( trans.sa_session, history )
                    trans.sa_session.flush()
                    if history not in shared_histories:
                        shared_histories.append( history )
        if send_to_err:
            msg += send_to_err
        return self.sharing( trans, histories=shared_histories, msg=msg )

    # ......................................................................... actions/orig. async
    @web.expose
    def delete_hidden_datasets( self, trans ):
        """
        This method deletes all hidden datasets in the current history.
        """
        count = 0
        for hda in trans.history.datasets:
            if not hda.visible and not hda.deleted and not hda.purged:
                hda.mark_deleted()
                count += 1
                trans.sa_session.add( hda )
                trans.log_event( "HDA id %s has been deleted" % hda.id )
        trans.sa_session.flush()
        return trans.show_ok_message( "%d hidden datasets have been deleted" % count, refresh_frames=['history'] )

    @web.expose
    def purge_deleted_datasets( self, trans ):
        count = 0
        if trans.app.config.allow_user_dataset_purge:
            for hda in trans.history.datasets:
                if not hda.deleted or hda.purged:
                    continue
                if trans.user:
                    trans.user.total_disk_usage -= hda.quota_amount( trans.user )
                hda.purged = True
                trans.sa_session.add( hda )
                trans.log_event( "HDA id %s has been purged" % hda.id )
                trans.sa_session.flush()
                if hda.dataset.user_can_purge:
                    try:
                        hda.dataset.full_delete()
                        trans.log_event( "Dataset id %s has been purged upon the the purge of HDA id %s" % ( hda.dataset.id, hda.id ) )
                        trans.sa_session.add( hda.dataset )
                    except:
                        log.exception( 'Unable to purge dataset (%s) on purge of hda (%s):' % ( hda.dataset.id, hda.id ) )
                count += 1
        return trans.show_ok_message( "%d datasets have been deleted permanently" % count, refresh_frames=['history'] )

    #TODO: use api instead
    @web.expose
    def delete_current( self, trans, purge=False ):
        """Delete just the active history -- this does not require a logged in user."""
        history = trans.get_history()
        if history.users_shared_with:
            return trans.show_error_message( "History (%s) has been shared with others, unshare it before deleting it.  " % history.name )
        if not history.deleted:
            history.deleted = True
            trans.sa_session.add( history )
            trans.sa_session.flush()
            trans.log_event( "History id %d marked as deleted" % history.id )
        if purge and trans.app.config.allow_user_dataset_purge:
            for hda in history.datasets:
                if trans.user:
                    trans.user.total_disk_usage -= hda.quota_amount( trans.user )
                hda.purged = True
                trans.sa_session.add( hda )
                trans.log_event( "HDA id %s has been purged" % hda.id )
                trans.sa_session.flush()
                if hda.dataset.user_can_purge:
                    try:
                        hda.dataset.full_delete()
                        trans.log_event( "Dataset id %s has been purged upon the the purge of HDA id %s" % ( hda.dataset.id, hda.id ) )
                        trans.sa_session.add( hda.dataset )
                    except:
                        log.exception( 'Unable to purge dataset (%s) on purge of hda (%s):' % ( hda.dataset.id, hda.id ) )
            history.purged = True
            self.sa_session.add( history )
            self.sa_session.flush()
        for hda in history.datasets:
            # Not all datasets have jobs associated with them (e.g., datasets imported from libraries).
            if hda.creating_job_associations:
                # HDA has associated job, so try marking it deleted.
                job = hda.creating_job_associations[0].job
                if job.history_id == history.id and job.state in [ trans.app.model.Job.states.QUEUED, trans.app.model.Job.states.RUNNING, trans.app.model.Job.states.NEW ]:
                    # No need to check other outputs since the job's parent history is this history
                    job.mark_deleted( trans.app.config.track_jobs_in_database )
                    trans.app.job_manager.job_stop_queue.put( job.id )

        # Regardless of whether it was previously deleted, get the most recent history or create a new one.
        most_recent_history = self.mgrs.histories.most_recent( trans, user=trans.user, deleted=False )
        if most_recent_history:
            trans.set_history( most_recent_history )
            return trans.show_ok_message( "History deleted, your most recent history is now active",
                refresh_frames=['history'] )

        trans.get_or_create_default_history()
        return trans.show_ok_message( "History deleted, a new history is active", refresh_frames=['history'] )

    @web.expose
    def unhide_datasets( self, trans, current=False, ids=None ):
        """Unhide the datasets in the active history -- this does not require a logged in user."""
        if not ids and galaxy.util.string_as_bool( current ):
            histories = [ trans.get_history() ]
            refresh_frames = ['history']
        else:
            raise NotImplementedError( "You can currently only unhide all the datasets of the current history." )
        for history in histories:
            history.unhide_datasets()
            trans.sa_session.add( history )
        trans.sa_session.flush()
        return trans.show_ok_message( "Your datasets have been unhidden.", refresh_frames=refresh_frames )
        #TODO: used in index.mako

    @web.expose
    def resume_paused_jobs( self, trans, current=False, ids=None ):
        """Resume paused jobs the active history -- this does not require a logged in user."""
        if not ids and galaxy.util.string_as_bool( current ):
            histories = [ trans.get_history() ]
            refresh_frames = ['history']
        else:
            raise NotImplementedError( "You can currently only resume all the datasets of the current history." )
        for history in histories:
            history.resume_paused_jobs()
            trans.sa_session.add( history )
        trans.sa_session.flush()
        return trans.show_ok_message( "Your jobs have been resumed.", refresh_frames=refresh_frames )
        #TODO: used in index.mako

    @web.expose
    @web.require_login( "rate items" )
    @web.json
    def rate_async( self, trans, id, rating ):
        """ Rate a history asynchronously and return updated community data. """
        history = self.get_history( trans, id, check_ownership=False, check_accessible=True )
        if not history:
            return trans.show_error_message( "The specified history does not exist." )
        # Rate history.
        history_rating = self.rate_item( trans.sa_session, trans.get_user(), history, rating )
        return self.get_ave_item_rating_data( trans.sa_session, history )
        #TODO: used in display_base.mako

    @web.expose
    # TODO: Remove require_login when users are warned that, if they are not
    # logged in, this will remove their current history.
    @web.require_login( "use Galaxy histories" )
    def import_archive( self, trans, **kwargs ):
        """ Import a history from a file archive. """
        # Set archive source and type.
        archive_file = kwargs.get( 'archive_file', None )
        archive_url = kwargs.get( 'archive_url', None )
        archive_source = None
        if archive_file:
            archive_source = archive_file
            archive_type = 'file'
        elif archive_url:
            archive_source = archive_url
            archive_type = 'url'
        # If no source to create archive from, show form to upload archive or specify URL.
        if not archive_source:
            return trans.show_form(
                web.FormBuilder( web.url_for(controller='history', action='import_archive'), "Import a History from an Archive", submit_text="Submit" ) \
                    .add_input( "text", "Archived History URL", "archive_url", value="", error=None )
                    # TODO: add support for importing via a file.
                    #.add_input( "file", "Archived History File", "archive_file", value=None, error=None )
                                )
        self.queue_history_import( trans, archive_type=archive_type, archive_source=archive_source )
        return trans.show_message( "Importing history from '%s'. \
                                    This history will be visible when the import is complete" % archive_source )
        #TODO: used in this file and index.mako

    @web.expose
    def export_archive( self, trans, id=None, gzip=True, include_hidden=False, include_deleted=False, preview=False ):
        """ Export a history to an archive. """
        #
        # Get history to export.
        #
        if id:
            history = self.get_history( trans, id, check_ownership=False, check_accessible=True )
        else:
            # Use current history.
            history = trans.history
            id = trans.security.encode_id( history.id )

        if not history:
            return trans.show_error_message( "This history does not exist or you cannot export this history." )

        #
        # If history has already been exported and it has not changed since export, stream it.
        #
        jeha = history.latest_export
        if jeha and jeha.up_to_date:
            if jeha.ready:
                if preview:
                    url = url_for( controller='history', action="export_archive", id=id, qualified=True )
                    return trans.show_message( "History Ready: '%(n)s'. Use this link to download \
                                                the archive or import it to another Galaxy server: \
                                                <a href='%(u)s'>%(u)s</a>" % ( { 'n' : history.name, 'u' : url } ) )
                else:
                    return self.serve_ready_history_export( trans, jeha )
            elif jeha.preparing:
                return trans.show_message( "Still exporting history %(n)s; please check back soon. Link: <a href='%(s)s'>%(s)s</a>" \
                        % ( { 'n' : history.name, 's' : url_for( controller='history', action="export_archive", id=id, qualified=True ) } ) )

        self.queue_history_export( trans, history, gzip=gzip, include_hidden=include_hidden, include_deleted=include_deleted )
        url = url_for( controller='history', action="export_archive", id=id, qualified=True )
        return trans.show_message( "Exporting History '%(n)s'. Use this link to download \
                                    the archive or import it to another Galaxy server: \
                                    <a href='%(u)s'>%(u)s</a>" % ( { 'n' : history.name, 'u' : url } ) )
        #TODO: used in this file and index.mako

    @web.expose
    @web.json
    @web.require_login( "get history name and link" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns history's name and link. """
        history = self.get_history( trans, id, False )
        if self.create_item_slug( trans.sa_session, history ):
            trans.sa_session.flush()
        return_dict = {
            "name" : history.name,
            "link" : url_for(controller='history', action="display_by_username_and_slug",
                username=history.user.username, slug=history.slug ) }
        return return_dict
        #TODO: used in page/editor.mako

    @web.expose
    @web.require_login( "set history's accessible flag" )
    def set_accessible_async( self, trans, id=None, accessible=False ):
        """ Set history's importable attribute and slug. """
        history = self.get_history( trans, id, True )
        # Only set if importable value would change; this prevents a change in the update_time unless attribute really changed.
        importable = accessible in ['True', 'true', 't', 'T'];
        if history and history.importable != importable:
            if importable:
                self._make_item_accessible( trans.sa_session, history )
            else:
                history.importable = importable
            trans.sa_session.flush()
        return
        #TODO: used in page/editor.mako

    @web.expose
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """

        history = self.get_history( trans, id, False, True )
        if history is None:
            raise web.httpexceptions.HTTPNotFound()

        # Get datasets.
        datasets = self.get_history_datasets( trans, history )
        # Get annotations.
        history.annotation = self.get_item_annotation_str( trans.sa_session, history.user, history )
        for dataset in datasets:
            dataset.annotation = self.get_item_annotation_str( trans.sa_session, history.user, dataset )
        return trans.stream_template_mako( "/history/item_content.mako", item = history, item_data = datasets )
        #TODO: used in embed_base.mako

    @web.expose
    def name_autocomplete_data( self, trans, q=None, limit=None, timestamp=None ):
        """Return autocomplete data for history names"""
        user = trans.get_user()
        if not user:
            return

        ac_data = ""
        for history in ( trans.sa_session.query( model.History )
                .filter_by( user=user )
                .filter( func.lower( model.History.name ).like(q.lower() + "%") ) ):
            ac_data = ac_data + history.name + "\n"
        return ac_data
        #TODO: used in grid_base.mako

    @web.expose
    def imp( self, trans, id=None, confirm=False, **kwd ):
        """Import another user's history via a shared URL"""
        msg = ""
        user = trans.get_user()
        user_history = trans.get_history()
        # Set referer message
        if 'referer' in kwd:
            referer = kwd['referer']
        else:
            referer = trans.request.referer
        if referer is not "":
            referer_message = "<a href='%s'>return to the previous page</a>" % escape(referer)
        else:
            referer_message = "<a href='%s'>go to Galaxy's start page</a>" % url_for( '/' )

        # include all datasets when copying?
        all_datasets = util.string_as_bool( kwd.get( 'all_datasets', False ) )

        # Do import.
        if not id:
            return trans.show_error_message( "You must specify a history you want to import.<br>You can %s." % referer_message, use_panels=True )
        import_history = self.get_history( trans, id, check_ownership=False, check_accessible=False )
        if not import_history:
            return trans.show_error_message( "The specified history does not exist.<br>You can %s." % referer_message, use_panels=True )
        # History is importable if user is admin or it's accessible. TODO: probably want to have app setting to enable admin access to histories.
        if not trans.user_is_admin() and not self.security_check( trans, import_history, check_ownership=False, check_accessible=True ):
            return trans.show_error_message( "You cannot access this history.<br>You can %s." % referer_message, use_panels=True )
        if user:
            #dan: I can import my own history.
            #if import_history.user_id == user.id:
            #    return trans.show_error_message( "You cannot import your own history.<br>You can %s." % referer_message, use_panels=True )
            new_history = import_history.copy( target_user=user, all_datasets=all_datasets )
            new_history.name = "imported: " + new_history.name
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                              .filter_by( session_id=galaxy_session.id, history_id=new_history.id ) \
                                              .first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            trans.sa_session.add( new_history )
            trans.sa_session.flush()
            # Set imported history to be user's current history.
            trans.set_history( new_history )
            return trans.show_ok_message(
                message="""History "%s" has been imported. <br>You can <a href="%s" onclick="parent.window.location='%s';">start using this history</a> or %s."""
                % ( new_history.name, web.url_for( '/' ), web.url_for( '/' ), referer_message ), use_panels=True )

        elif not user_history or not user_history.datasets or confirm:
            #TODO:?? should anon-users be allowed to include deleted datasets when importing?
            #new_history = import_history.copy( activatable=include_deleted )
            new_history = import_history.copy()
            new_history.name = "imported: " + new_history.name
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                              .filter_by( session_id=galaxy_session.id, history_id=new_history.id ) \
                                              .first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            trans.sa_session.add( new_history )
            trans.sa_session.flush()
            trans.set_history( new_history )
            return trans.show_ok_message(
                message="""History "%s" has been imported. <br>You can <a href="%s">start using this history</a> or %s."""
                % ( new_history.name, web.url_for( '/' ), referer_message ), use_panels=True )
        return trans.show_warn_message( """
            Warning! If you import this history, you will lose your current
            history. <br>You can <a href="%s">continue and import this history</a> or %s.
            """ % ( web.url_for(controller='history', action='imp',  id=id, confirm=True, referer=trans.request.referer ), referer_message ), use_panels=True )
        #TODO: used in history/view, display, embed

    @web.expose
    @web.require_login( "rename histories" )
    def rename( self, trans, id=None, name=None, **kwd ):
        user = trans.get_user()
        if not id:
            # Default to the current history
            history = trans.get_history()
            if not history.user:
                return trans.show_error_message( "You must save your history before renaming it." )
            id = trans.security.encode_id( history.id )
        id = galaxy.util.listify( id )
        name = galaxy.util.listify( name )
        histories = []
        cur_names = []
        for history_id in id:
            history = self.get_history( trans, history_id )
            if history and history.user_id == user.id:
                histories.append( history )
                cur_names.append( history.get_display_name() )
        if not name or len( histories ) != len( name ):
            return trans.fill_template( "/history/rename.mako", histories=histories )
        change_msg = ""
        for i in range(len(histories)):
            if histories[i].user_id == user.id:
                if name[i] == histories[i].get_display_name():
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" is already named: "+name[i]+"</p>"
                elif name[i] not in [None,'',' ']:
                    name[i] = escape(name[i])
                    histories[i].name = sanitize_html( name[i] )
                    trans.sa_session.add( histories[i] )
                    trans.sa_session.flush()
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" renamed to: "+name[i]+"</p>"
                    trans.log_event( "History renamed: id: %s, renamed to: '%s'" % (str(histories[i].id), name[i] ) )
                else:
                    change_msg = change_msg + "<p>You must specify a valid name for History: "+cur_names[i]+"</p>"
            else:
                change_msg = change_msg + "<p>History: "+cur_names[i]+" does not appear to belong to you.</p>"
        return trans.show_message( "<p>%s" % change_msg, refresh_frames=['history'] )

    @web.expose
    @web.require_login( "copy shared Galaxy history" )
    def copy( self, trans, id=None, **kwd ):
        """Copy one or more histories"""
        params = Params( kwd )
        # If copy_choice was not specified, display form passing along id
        # argument
        copy_choice = params.get( 'copy_choice', None )
        if not copy_choice:
            return trans.fill_template( "/history/copy.mako", id_argument=id )

        # Extract histories for id argument, defaulting to current
        if id is None:
            histories = [ trans.history ]
        else:
            ids = galaxy.util.listify( id )
            histories = []
            for history_id in ids:
                history = self.get_history( trans, history_id, check_ownership=False )
                histories.append( history )
        user = trans.get_user()
        for history in histories:
            if history.user == user:
                owner = True
            else:
                if trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ) \
                                   .filter_by( user=user, history=history ) \
                                   .count() == 0:
                    return trans.show_error_message( "The history you are attempting to copy is not owned by you or shared with you.  " )
                owner = False
            name = "Copy of '%s'" % history.name
            if not owner:
                name += " shared by '%s'" % history.user.email
            if copy_choice == 'activatable':
                new_history = history.copy( name=name, target_user=user, activatable=True )
            elif copy_choice == 'active':
                name += " (active items only)"
                new_history = history.copy( name=name, target_user=user )
        if len( histories ) == 1:
            switch_url = url_for( controller="history", action="switch_to_history", hist_id=trans.security.encode_id( new_history.id ) )
            msg = 'New history "<a href="%s" target="_top">%s</a>" has been created.' % ( switch_url, new_history.name )
        else:
            msg = 'Copied and created %d new histories.' % len( histories )
        return trans.show_ok_message( msg )


    # ------------------------------------------------------------------------- current history
    @web.expose
    @web.require_login( "switch to a history" )
    def switch_to_history( self, trans, hist_id=None ):
        """
        """
        self.set_as_current( trans, id=hist_id )
        return trans.response.send_redirect( url_for( "/" ) )

    def get_item( self, trans, id ):
        return self.get_history( trans, id )
        #TODO: override of base ui controller?

    def history_data( self, trans, history ):
        """
        """
        #TODO: to manager
        history_data = self.get_history_dict( trans, history )
        encoded_history_id = trans.security.encode_id( history.id )
        history_data[ 'contents_url' ] = url_for( 'history_contents', history_id=encoded_history_id )
        return history_data

    #TODO: combine these next two - poss. with a redirect flag
    @web.require_login( "switch to a history" )
    @web.json
    def set_as_current( self, trans, id=None ):
        """
        """
        history = self.get_history( trans, id )
        trans.set_history( history )
        return self.history_data( trans, history )

    @web.json
    def current_history_json( self, trans ):
        """
        """
        history = trans.get_history( create=True )
        return self.history_data( trans, history )

    @web.json
    def create_new_current( self, trans, name=None ):
        """
        """
        return self.history_data( trans, trans.new_history( name ) )

    #TODO: /history/current to do all of the above: if ajax, return json; if post, read id and set to current
