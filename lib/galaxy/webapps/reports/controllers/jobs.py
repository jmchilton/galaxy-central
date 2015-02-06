import calendar
from datetime import datetime, date, timedelta
from galaxy.web.base.controller import BaseUIController, web
from galaxy import model, util
from galaxy.web.framework.helpers import grids
from galaxy.model.orm import and_, not_, or_
import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy as sa
import logging
log = logging.getLogger( __name__ )


class SpecifiedDateListGrid( grids.Grid ):

    class JobIdColumn( grids.IntegerColumn ):

        def get_value( self, trans, grid, job ):
            return job.id

    class StateColumn( grids.TextColumn ):

        def get_value( self, trans, grid, job ):
            return '<div class="count-box state-color-%s">%s</div>' % ( job.state, job.state )

        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'Unfinished':
                return query.filter( not_( or_( model.Job.table.c.state == model.Job.states.OK,
                                                model.Job.table.c.state == model.Job.states.ERROR,
                                                model.Job.table.c.state == model.Job.states.DELETED ) ) )
            return query

    class ToolColumn( grids.TextColumn ):

        def get_value( self, trans, grid, job ):
            return job.tool_id

    class CreateTimeColumn( grids.DateTimeColumn ):

        def get_value( self, trans, grid, job ):
            return job.create_time.strftime("%b %d, %Y, %H:%M:%S")

    class UserColumn( grids.GridColumn ):

        def get_value( self, trans, grid, job ):
            if job.user:
                return job.user.email
            return 'anonymous'

    class EmailColumn( grids.GridColumn ):

        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Job.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )

    class SpecifiedDateColumn( grids.GridColumn ):

        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            # We are either filtering on a date like YYYY-MM-DD or on a month like YYYY-MM,
            # so we need to figure out which type of date we have
            if column_filter.count( '-' ) == 2:  # We are filtering on a date like YYYY-MM-DD
                year, month, day = map( int, column_filter.split( "-" ) )
                start_date = date( year, month, day )
                end_date = start_date + timedelta( days=1 )
            if column_filter.count( '-' ) == 1:  # We are filtering on a month like YYYY-MM
                year, month = map( int, column_filter.split( "-" ) )
                start_date = date( year, month, 1 )
                end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )

            return query.filter( and_( self.model_class.table.c.create_time >= start_date,
                                       self.model_class.table.c.create_time < end_date ) )

    # Grid definition
    use_async = False
    model_class = model.Job
    title = "Jobs"
    template = '/webapps/reports/grid.mako'
    default_sort_key = "id"
    columns = [
        JobIdColumn( "Id",
                     key="id",
                     link=( lambda item: dict( operation="job_info", id=item.id, webapp="reports" ) ),
                     attach_popup=False,
                     filterable="advanced" ),
        StateColumn( "State",
                     key="state",
                     attach_popup=False ),
        ToolColumn( "Tool Id",
                    key="tool_id",
                    link=( lambda item: dict( operation="tool_per_month", id=item.id, webapp="reports" ) ),
                    attach_popup=False ),
        CreateTimeColumn( "Creation Time",
                          key="create_time",
                          attach_popup=False ),
        UserColumn( "User",
                    key="email",
                    model_class=model.User,
                    link=( lambda item: dict( operation="user_per_month", id=item.id, webapp="reports" ) ),
                    attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        SpecifiedDateColumn( "Specified Date",
                             key="specified_date",
                             visible=False ),
        EmailColumn( "Email",
                     key="email",
                     model_class=model.User,
                     visible=False ),
        grids.StateColumn( "State",
                           key="state",
                           visible=False,
                           filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search",
                                                cols_to_filter=[ columns[1], columns[2] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    standard_filters = []
    default_filter = { 'specified_date': 'All' }
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

    def build_initial_query( self, trans, **kwd ):
        params = util.Params( kwd )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        monitor_user_id = get_monitor_id( trans, monitor_email )
        return trans.sa_session.query( self.model_class ) \
                               .join( model.User ) \
                               .filter( model.Job.table.c.user_id != monitor_user_id )\
                               .enable_eagerloads( False )


class Jobs( BaseUIController ):

    """
    Class contains functions for querying data requested by user via the webapp. It exposes the functions and
    responds to requests with the filled .mako templates.
    """

    specified_date_list_grid = SpecifiedDateListGrid()

    @web.expose
    def specified_date_handler( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if 'f-specified_date' in kwd and 'specified_date' not in kwd:
            # The user clicked a State link in the Advanced Search box, so 'specified_date'
            # will have been eliminated.
            pass
        elif 'specified_date' not in kwd:
            kwd[ 'f-specified_date' ] = 'All'
        else:
            kwd[ 'f-specified_date' ] = kwd[ 'specified_date' ]
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='job_info',
                                                                  **kwd ) )
            elif operation == "tool_for_month":
                kwd[ 'f-tool_id' ] = kwd[ 'tool_id' ]
            elif operation == "tool_per_month":
                # The received id is the job id, so we need to get the job's tool_id.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'tool_id' ] = job.tool_id
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='tool_per_month',
                                                                  **kwd ) )
            elif operation == "user_for_month":
                kwd[ 'f-email' ] = util.restore_text( kwd[ 'email' ] )
            elif operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                if job.user:
                    kwd[ 'email' ] = job.user.email
                else:
                    kwd[ 'email' ] = None  # For anonymous users
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='user_per_month',
                                                                  **kwd ) )
            elif operation == "specified_date_in_error":
                kwd[ 'f-state' ] = 'error'
            elif operation == "unfinished":
                kwd[ 'f-state' ] = 'Unfinished'
        return self.specified_date_list_grid( trans, **kwd )

    @web.expose
    def specified_month_all( self, trans, **kwd ):
        """
        Queries the DB for all jobs in given month, defaults to current month.
        """
        message = ''

        params = util.Params( kwd )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id( trans, monitor_email )

        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        specified_month = specified_date[ :7 ]
        year, month = map( int, specified_month.split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )

        month_jobs = sa.select( ( sa.func.date( model.Job.table.c.create_time ).label( 'date' ),
                                  sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                                whereclause=sa.and_( model.Job.table.c.user_id != monitor_user_id,
                                                     model.Job.table.c.create_time >= start_date,
                                                     model.Job.table.c.create_time < end_date ),
                                from_obj=[ model.Job.table ],
                                group_by=[ 'date' ],
                                order_by=[ sa.desc( 'date' ) ] )

        jobs = []
        for row in month_jobs.execute():
            jobs.append( ( row.date.strftime( "%A" ),
                           row.date.strftime( "%d" ),
                           row.total_jobs,
                           row.date
                           ) )
        return trans.fill_template( '/webapps/reports/jobs_specified_month_all.mako',
                                    month_label=month_label,
                                    year_label=year_label,
                                    month=month,
                                    jobs=jobs,
                                    is_user_jobs_only=monitor_user_id,
                                    message=message )

    @web.expose
    def specified_month_in_error( self, trans, **kwd ):
        """
        Queries the DB for the user jobs in error.
        """
        message = ''
        params = util.Params( kwd )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )

        # In case we don't know which is the monitor user we will query for all jobs instead
        monitor_user_id = get_monitor_id( trans, monitor_email )

        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        specified_month = specified_date[ :7 ]
        year, month = map( int, specified_month.split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )

        month_jobs_in_error = sa.select( ( sa.func.date( model.Job.table.c.create_time ).label( 'date' ),
                                           sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                                         whereclause=sa.and_( model.Job.table.c.user_id != monitor_user_id,
                                                              model.Job.table.c.state == 'error',
                                                              model.Job.table.c.create_time >= start_date,
                                                              model.Job.table.c.create_time < end_date ),
                                         from_obj=[ model.Job.table ],
                                         group_by=[ 'date' ],
                                         order_by=[ sa.desc( 'date' ) ] )

        jobs = []
        for row in month_jobs_in_error.execute():
            jobs.append( ( row.date.strftime( "%A" ),
                           row.date,
                           row.total_jobs,
                           row.date.strftime( "%d" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_specified_month_in_error.mako',
                                    month_label=month_label,
                                    year_label=year_label,
                                    month=month,
                                    jobs=jobs,
                                    message=message,
                                    is_user_jobs_only=monitor_user_id )

    @web.expose
    def per_month_all( self, trans, **kwd ):
        """
        Queries the DB for all jobs. Avoids monitor jobs.
        """

        message = ''
        params = util.Params( kwd )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id( trans, monitor_email )

        jobs_by_month = sa.select( ( sa.func.date_trunc( 'month', model.Job.table.c.create_time ).label( 'date' ),
                                     sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                                   whereclause=model.Job.table.c.user_id != monitor_user_id,
                                   from_obj=[ model.Job.table ],
                                   group_by=[ 'date' ],
                                   order_by=[ sa.desc( 'date' ) ] )

        jobs = []
        for row in jobs_by_month.execute():
            jobs.append( (
                row.date.strftime( "%Y-%m" ),
                row.total_jobs,
                row.date.strftime( "%B" ),
                row.date.strftime( "%y" )
            ) )

        return trans.fill_template( '/webapps/reports/jobs_per_month_all.mako',
                                    jobs=jobs,
                                    is_user_jobs_only=monitor_user_id,
                                    message=message )

    @web.expose
    def per_month_in_error( self, trans, **kwd ):
        """
        Queries the DB for user jobs in error. Filters out monitor jobs.
        """

        message = ''
        params = util.Params( kwd )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id( trans, monitor_email )

        jobs_in_error_by_month = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                                              sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                                            whereclause=sa.and_( model.Job.table.c.state == 'error',
                                                                 model.Job.table.c.user_id != monitor_user_id ),
                                            from_obj=[ model.Job.table ],
                                            group_by=[ sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ) ],
                                            order_by=[ sa.desc( 'date' ) ] )

        jobs = []
        for row in jobs_in_error_by_month.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ),
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%y" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_per_month_in_error.mako',
                                    jobs=jobs,
                                    message=message,
                                    is_user_jobs_only=monitor_user_id )

    @web.expose
    def per_user( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )

        jobs = []
        jobs_per_user = sa.select( ( model.User.table.c.email.label( 'user_email' ),
                                     sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                                   from_obj=[ sa.outerjoin( model.Job.table, model.User.table ) ],
                                   group_by=[ 'user_email' ],
                                   order_by=[ sa.desc( 'total_jobs' ), 'user_email' ] )
        for row in jobs_per_user.execute():
            if ( row.user_email is None ):
                jobs.append( ( 'Anonymous',
                               row.total_jobs ) )
            elif ( row.user_email == monitor_email ):
                continue
            else:
                jobs.append( ( row.user_email,
                               row.total_jobs ) )
        return trans.fill_template( '/webapps/reports/jobs_per_user.mako',
                                    jobs=jobs,
                                    message=message )

    @web.expose
    def user_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        email = util.restore_text( params.get( 'email', '' ) )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause=sa.and_( model.Job.table.c.session_id == model.GalaxySession.table.c.id,
                                            model.GalaxySession.table.c.user_id == model.User.table.c.id,
                                            model.User.table.c.email == email
                                            ),
                       from_obj=[ sa.join( model.Job.table, model.User.table ) ],
                       group_by=[ sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ) ],
                       order_by=[ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ),
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_user_per_month.mako',
                                    email=util.sanitize_text( email ),
                                    jobs=jobs, message=message )

    @web.expose
    def per_tool( self, trans, **kwd ):
        message = ''

        params = util.Params( kwd )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id( trans, monitor_email )

        jobs = []
        q = sa.select( ( model.Job.table.c.tool_id.label( 'tool_id' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause=model.Job.table.c.user_id != monitor_user_id,
                       from_obj=[ model.Job.table ],
                       group_by=[ 'tool_id' ],
                       order_by=[ 'tool_id' ] )
        for row in q.execute():
            jobs.append( ( row.tool_id,
                           row.total_jobs ) )
        return trans.fill_template( '/webapps/reports/jobs_per_tool.mako',
                                    jobs=jobs,
                                    message=message,
                                    is_user_jobs_only=monitor_user_id )

    @web.expose
    def tool_per_month( self, trans, **kwd ):
        message = ''

        params = util.Params( kwd )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id( trans, monitor_email )

        tool_id = params.get( 'tool_id', 'Add a column1' )
        specified_date = params.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause=sa.and_( model.Job.table.c.tool_id == tool_id,
                                            model.Job.table.c.user_id != monitor_user_id ),
                       from_obj=[ model.Job.table ],
                       group_by=[ sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ) ],
                       order_by=[ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ),
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_tool_per_month.mako',
                                    specified_date=specified_date,
                                    tool_id=tool_id,
                                    jobs=jobs,
                                    message=message,
                                    is_user_jobs_only=monitor_user_id )

    @web.expose
    def job_info( self, trans, **kwd ):
        message = ''
        job = trans.sa_session.query( model.Job ) \
                              .get( trans.security.decode_id( kwd.get( 'id', '' ) ) )
        return trans.fill_template( '/webapps/reports/job_info.mako',
                                    job=job,
                                    message=message )

# ---- Utility methods -------------------------------------------------------


def get_job( trans, id ):
    return trans.sa_session.query( trans.model.Job ).get( trans.security.decode_id( id ) )


def get_monitor_id( trans, monitor_email ):
    """
    A convenience method to obtain the monitor job id.
    """
    monitor_user_id = None
    monitor_row = trans.sa_session.query( trans.model.User.table.c.id ) \
        .filter( trans.model.User.table.c.email == monitor_email ) \
        .first()
    if monitor_row is not None:
        monitor_user_id = monitor_row[0]
    return monitor_user_id
