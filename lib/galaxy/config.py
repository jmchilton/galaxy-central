"""
Universe configuration builder.
"""
# absolute_import needed for tool_shed package.
from __future__ import absolute_import

import ConfigParser
import logging
import logging.config
import os
import re
import socket
import string
import sys
import tempfile
from datetime import timedelta
from galaxy import eggs
from galaxy.util import listify
from galaxy.util import string_as_bool
from galaxy.util.dbkeys import GenomeBuilds
from galaxy.web.formatting import expand_pretty_datetime_format


log = logging.getLogger( __name__ )


def resolve_path( path, root ):
    """If 'path' is relative make absolute by prepending 'root'"""
    if not( os.path.isabs( path ) ):
        path = os.path.join( root, path )
    return path


class ConfigurationError( Exception ):
    pass


class Configuration( object ):
    deprecated_options = ( 'database_file', )

    def __init__( self, **kwargs ):
        self.config_dict = kwargs
        self.root = kwargs.get( 'root_dir', '.' )

        # Resolve paths of other config files
        self.__parse_config_file_options( kwargs )

        # Collect the umask and primary gid from the environment
        self.umask = os.umask( 077 )  # get the current umask
        os.umask( self.umask )  # can't get w/o set, so set it back
        self.gid = os.getgid()  # if running under newgrp(1) we'll need to fix the group of data created on the cluster

        # Database related configuration
        self.database = resolve_path( kwargs.get( "database_file", "database/universe.sqlite" ), self.root )
        self.database_connection = kwargs.get( "database_connection", False )
        self.database_engine_options = get_database_engine_options( kwargs )
        self.database_create_tables = string_as_bool( kwargs.get( "database_create_tables", "True" ) )
        self.database_query_profiling_proxy = string_as_bool( kwargs.get( "database_query_profiling_proxy", "False" ) )

        # Don't set this to true for production databases, but probably should
        # default to True for sqlite databases.
        self.database_auto_migrate = string_as_bool( kwargs.get( "database_auto_migrate", "False" ) )

        # Install database related configuration (if different).
        self.install_database_connection = kwargs.get( "install_database_connection", None )
        self.install_database_engine_options = get_database_engine_options( kwargs, model_prefix="install_" )

        # Where dataset files are stored
        self.file_path = resolve_path( kwargs.get( "file_path", "database/files" ), self.root )
        self.new_file_path = resolve_path( kwargs.get( "new_file_path", "database/tmp" ), self.root )
        tempfile.tempdir = self.new_file_path
        self.openid_consumer_cache_path = resolve_path( kwargs.get( "openid_consumer_cache_path", "database/openid_consumer_cache" ), self.root )
        self.cookie_path = kwargs.get( "cookie_path", "/" )
        # Galaxy OpenID settings
        self.enable_openid = string_as_bool( kwargs.get( 'enable_openid', False ) )
        self.enable_quotas = string_as_bool( kwargs.get( 'enable_quotas', False ) )
        self.enable_unique_workflow_defaults = string_as_bool( kwargs.get( 'enable_unique_workflow_defaults', False ) )
        self.tool_path = resolve_path( kwargs.get( "tool_path", "tools" ), self.root )
        self.tool_data_path = resolve_path( kwargs.get( "tool_data_path", "tool-data" ), os.getcwd() )
        self.builds_file_path = resolve_path( kwargs.get( "builds_file_path", os.path.join( self.tool_data_path, 'shared', 'ucsc', 'builds.txt') ), self.root )
        self.len_file_path = resolve_path( kwargs.get( "len_file_path", os.path.join( self.tool_data_path, 'shared', 'ucsc', 'chrom') ), self.root )
        self.test_conf = resolve_path( kwargs.get( "test_conf", "" ), self.root )
        # The value of migrated_tools_config is the file reserved for containing only those tools that have been eliminated from the distribution
        # and moved to the tool shed.
        self.integrated_tool_panel_config = resolve_path( kwargs.get( 'integrated_tool_panel_config', 'integrated_tool_panel.xml' ), self.root )
        self.toolbox_filter_base_modules = listify( kwargs.get( "toolbox_filter_base_modules", "galaxy.tools.filters,galaxy.tools.toolbox.filters" ) )
        self.tool_filters = listify( kwargs.get( "tool_filters", [] ), do_strip=True )
        self.tool_label_filters = listify( kwargs.get( "tool_label_filters", [] ), do_strip=True )
        self.tool_section_filters = listify( kwargs.get( "tool_section_filters", [] ), do_strip=True )

        self.user_tool_filters = listify( kwargs.get( "user_tool_filters", [] ), do_strip=True )
        self.user_label_filters = listify( kwargs.get( "user_tool_label_filters", [] ), do_strip=True )
        self.user_section_filters = listify( kwargs.get( "user_tool_section_filters", [] ), do_strip=True )

        # Check for tools defined in the above non-shed tool configs (i.e., tool_conf.xml) tht have
        # been migrated from the Galaxy code distribution to the Tool Shed.
        self.check_migrate_tools = string_as_bool( kwargs.get( 'check_migrate_tools', True ) )
        self.shed_tool_data_path = kwargs.get( "shed_tool_data_path", None )
        self.x_frame_options = kwargs.get( "x_frame_options", "SAMEORIGIN" )
        if self.shed_tool_data_path:
            self.shed_tool_data_path = resolve_path( self.shed_tool_data_path, self.root )
        else:
            self.shed_tool_data_path = self.tool_data_path
        self.manage_dependency_relationships = string_as_bool( kwargs.get( 'manage_dependency_relationships', False ) )
        self.running_functional_tests = string_as_bool( kwargs.get( 'running_functional_tests', False ) )
        self.hours_between_check = kwargs.get( 'hours_between_check', 12 )
        if isinstance( self.hours_between_check, basestring ):
            self.hours_between_check = float( self.hours_between_check )
        try:
            if isinstance( self.hours_between_check, int ):
                if self.hours_between_check < 1 or self.hours_between_check > 24:
                    self.hours_between_check = 12
            elif isinstance( self.hours_between_check, float ):
                # If we're running functional tests, the minimum hours between check should be reduced to 0.001, or 3.6 seconds.
                if self.running_functional_tests:
                    if self.hours_between_check < 0.001 or self.hours_between_check > 24.0:
                        self.hours_between_check = 12.0
                else:
                    if self.hours_between_check < 1.0 or self.hours_between_check > 24.0:
                        self.hours_between_check = 12.0
            else:
                self.hours_between_check = 12
        except:
            self.hours_between_check = 12
        self.update_integrated_tool_panel = kwargs.get( "update_integrated_tool_panel", True )
        self.enable_data_manager_user_view = string_as_bool( kwargs.get( "enable_data_manager_user_view", "False" ) )
        self.galaxy_data_manager_data_path = kwargs.get( 'galaxy_data_manager_data_path', self.tool_data_path )
        self.tool_secret = kwargs.get( "tool_secret", "" )
        self.id_secret = kwargs.get( "id_secret", "USING THE DEFAULT IS NOT SECURE!" )
        self.retry_metadata_internally = string_as_bool( kwargs.get( "retry_metadata_internally", "True" ) )
        self.use_remote_user = string_as_bool( kwargs.get( "use_remote_user", "False" ) )
        self.normalize_remote_user_email = string_as_bool( kwargs.get( "normalize_remote_user_email", "False" ) )
        self.remote_user_maildomain = kwargs.get( "remote_user_maildomain", None )
        self.remote_user_header = kwargs.get( "remote_user_header", 'HTTP_REMOTE_USER' )
        self.remote_user_logout_href = kwargs.get( "remote_user_logout_href", None )
        self.remote_user_secret = kwargs.get( "remote_user_secret", None )
        self.require_login = string_as_bool( kwargs.get( "require_login", "False" ) )
        self.allow_user_creation = string_as_bool( kwargs.get( "allow_user_creation", "True" ) )
        self.allow_user_deletion = string_as_bool( kwargs.get( "allow_user_deletion", "False" ) )
        self.allow_user_dataset_purge = string_as_bool( kwargs.get( "allow_user_dataset_purge", "False" ) )
        self.allow_user_impersonation = string_as_bool( kwargs.get( "allow_user_impersonation", "False" ) )
        self.new_user_dataset_access_role_default_private = string_as_bool( kwargs.get( "new_user_dataset_access_role_default_private", "False" ) )
        self.collect_outputs_from = [ x.strip() for x in kwargs.get( 'collect_outputs_from', 'new_file_path,job_working_directory' ).lower().split(',') ]
        self.template_path = resolve_path( kwargs.get( "template_path", "templates" ), self.root )
        self.template_cache = resolve_path( kwargs.get( "template_cache_path", "database/compiled_templates" ), self.root )
        self.local_job_queue_workers = int( kwargs.get( "local_job_queue_workers", "5" ) )
        self.cluster_job_queue_workers = int( kwargs.get( "cluster_job_queue_workers", "3" ) )
        self.job_queue_cleanup_interval = int( kwargs.get("job_queue_cleanup_interval", "5") )
        self.cluster_files_directory = os.path.abspath( kwargs.get( "cluster_files_directory", "database/pbs" ) )
        self.job_working_directory = resolve_path( kwargs.get( "job_working_directory", "database/job_working_directory" ), self.root )
        self.cleanup_job = kwargs.get( "cleanup_job", "always" )
        self.container_image_cache_path = self.resolve_path( kwargs.get( "container_image_cache_path", "database/container_images" ) )
        self.outputs_to_working_directory = string_as_bool( kwargs.get( 'outputs_to_working_directory', False ) )
        self.output_size_limit = int( kwargs.get( 'output_size_limit', 0 ) )
        self.retry_job_output_collection = int( kwargs.get( 'retry_job_output_collection', 0 ) )
        self.job_walltime = kwargs.get( 'job_walltime', None )
        self.job_walltime_delta = None
        if self.job_walltime is not None:
            h, m, s = [ int( v ) for v in self.job_walltime.split( ':' ) ]
            self.job_walltime_delta = timedelta( 0, s, 0, 0, m, h )
        self.admin_users = kwargs.get( "admin_users", "" )
        self.admin_users_list = [u.strip() for u in self.admin_users.split(',') if u]
        self.mailing_join_addr = kwargs.get('mailing_join_addr', 'galaxy-announce-join@bx.psu.edu')
        self.error_email_to = kwargs.get( 'error_email_to', None )
        self.activation_email = kwargs.get( 'activation_email', None )
        self.user_activation_on = string_as_bool( kwargs.get( 'user_activation_on', False ) )
        self.activation_grace_period = kwargs.get( 'activation_grace_period', None )
        self.inactivity_box_content = kwargs.get( 'inactivity_box_content', None )
        self.terms_url = kwargs.get( 'terms_url', None )
        self.instance_resource_url = kwargs.get( 'instance_resource_url', None )
        self.registration_warning_message = kwargs.get( 'registration_warning_message', None )
        self.ga_code = kwargs.get( 'ga_code', None )
        self.session_duration = int(kwargs.get( 'session_duration', 0 ))
        #  Get the disposable email domains blacklist file and its contents
        self.blacklist_location = kwargs.get( 'blacklist_file', None )
        self.blacklist_content = None
        if self.blacklist_location is not None:
            self.blacklist_file = resolve_path( kwargs.get( 'blacklist_file', None ), self.root )
            try:
                with open( self.blacklist_file ) as blacklist:
                    self.blacklist_content = [ line.rstrip() for line in blacklist.readlines() ]
            except IOError:
                    print ( "CONFIGURATION ERROR: Can't open supplied blacklist file from path: " + str( self.blacklist_file ) )
        self.smtp_server = kwargs.get( 'smtp_server', None )
        self.smtp_username = kwargs.get( 'smtp_username', None )
        self.smtp_password = kwargs.get( 'smtp_password', None )
        self.smtp_ssl = kwargs.get( 'smtp_ssl', None )
        self.track_jobs_in_database = kwargs.get( 'track_jobs_in_database', 'None' )
        self.start_job_runners = listify(kwargs.get( 'start_job_runners', '' ))
        self.expose_dataset_path = string_as_bool( kwargs.get( 'expose_dataset_path', 'False' ) )
        # External Service types used in sample tracking
        self.external_service_type_path = resolve_path( kwargs.get( 'external_service_type_path', 'external_service_types' ), self.root )
        # Tasked job runner.
        self.use_tasked_jobs = string_as_bool( kwargs.get( 'use_tasked_jobs', False ) )
        self.local_task_queue_workers = int(kwargs.get("local_task_queue_workers", 2))
        self.commands_in_new_shell = string_as_bool( kwargs.get( 'enable_beta_tool_command_isolation', "False" ) )
        # The transfer manager and deferred job queue
        self.enable_beta_job_managers = string_as_bool( kwargs.get( 'enable_beta_job_managers', 'False' ) )
        # These workflow modules should not be considered part of Galaxy's
        # public API yet - the module state definitions may change and
        # workflows built using these modules may not function in the
        # future.
        self.enable_beta_workflow_modules = string_as_bool( kwargs.get( 'enable_beta_workflow_modules', 'False' ) )
        # These are not even beta - just experiments - don't use them unless
        # you want yours tools to be broken in the future.
        self.enable_beta_tool_formats = string_as_bool( kwargs.get( 'enable_beta_tool_formats', 'False' ) )

        # Certain modules such as the pause module will automatically cause
        # workflows to be scheduled in job handlers the way all workflows will
        # be someday - the following two properties can also be used to force this
        # behavior in under conditions - namely for workflows that have a minimum
        # number of steps or that consume collections.
        self.force_beta_workflow_scheduled_min_steps = int( kwargs.get( 'force_beta_workflow_scheduled_min_steps', '250' ) )
        self.force_beta_workflow_scheduled_for_collections = string_as_bool( kwargs.get( 'force_beta_workflow_scheduled_for_collections', 'False' ) )

        # Per-user Job concurrency limitations
        self.cache_user_job_count = string_as_bool( kwargs.get( 'cache_user_job_count', False ) )
        self.user_job_limit = int( kwargs.get( 'user_job_limit', 0 ) )
        self.registered_user_job_limit = int( kwargs.get( 'registered_user_job_limit', self.user_job_limit ) )
        self.anonymous_user_job_limit = int( kwargs.get( 'anonymous_user_job_limit', self.user_job_limit ) )
        self.default_cluster_job_runner = kwargs.get( 'default_cluster_job_runner', 'local:///' )
        self.pbs_application_server = kwargs.get('pbs_application_server', "" )
        self.pbs_dataset_server = kwargs.get('pbs_dataset_server', "" )
        self.pbs_dataset_path = kwargs.get('pbs_dataset_path', "" )
        self.pbs_stage_path = kwargs.get('pbs_stage_path', "" )
        self.drmaa_external_runjob_script = kwargs.get('drmaa_external_runjob_script', None )
        self.drmaa_external_killjob_script = kwargs.get('drmaa_external_killjob_script', None)
        self.external_chown_script = kwargs.get('external_chown_script', None)
        self.environment_setup_file = kwargs.get( 'environment_setup_file', None )
        self.use_heartbeat = string_as_bool( kwargs.get( 'use_heartbeat', 'False' ) )
        self.log_actions = string_as_bool( kwargs.get( 'log_actions', 'False' ) )
        self.log_events = string_as_bool( kwargs.get( 'log_events', 'False' ) )
        self.sanitize_all_html = string_as_bool( kwargs.get( 'sanitize_all_html', True ) )
        self.serve_xss_vulnerable_mimetypes = string_as_bool( kwargs.get( 'serve_xss_vulnerable_mimetypes', False ) )
        self.trust_ipython_notebook_conversion = string_as_bool( kwargs.get( 'trust_ipython_notebook_conversion', False ) )
        self.enable_old_display_applications = string_as_bool( kwargs.get( "enable_old_display_applications", "True" ) )
        self.brand = kwargs.get( 'brand', None )
        self.welcome_url = kwargs.get( 'welcome_url', '/static/welcome.html' )
        # Configuration for the message box directly below the masthead.
        self.message_box_visible = kwargs.get( 'message_box_visible', False )
        self.message_box_content = kwargs.get( 'message_box_content', None )
        self.message_box_class = kwargs.get( 'message_box_class', 'info' )
        self.support_url = kwargs.get( 'support_url', 'https://wiki.galaxyproject.org/Support' )
        self.wiki_url = kwargs.get( 'wiki_url', 'http://wiki.galaxyproject.org/' )
        self.blog_url = kwargs.get( 'blog_url', None )
        self.screencasts_url = kwargs.get( 'screencasts_url', None )
        self.library_import_dir = kwargs.get( 'library_import_dir', None )
        self.user_library_import_dir = kwargs.get( 'user_library_import_dir', None )
        # Searching data libraries
        self.enable_lucene_library_search = string_as_bool( kwargs.get( 'enable_lucene_library_search', False ) )
        self.enable_whoosh_library_search = string_as_bool( kwargs.get( 'enable_whoosh_library_search', False ) )
        self.whoosh_index_dir = resolve_path( kwargs.get( "whoosh_index_dir", "database/whoosh_indexes" ), self.root )
        self.ftp_upload_dir = kwargs.get( 'ftp_upload_dir', None )
        self.ftp_upload_dir_identifier = kwargs.get( 'ftp_upload_dir_identifier', 'email' )  # attribute on user - email, username, id, etc...
        self.ftp_upload_site = kwargs.get( 'ftp_upload_site', None )
        self.allow_library_path_paste = kwargs.get( 'allow_library_path_paste', False )
        self.disable_library_comptypes = kwargs.get( 'disable_library_comptypes', '' ).lower().split( ',' )
        self.watch_tools = string_as_bool( kwargs.get( 'watch_tools', False ) )
        # On can mildly speed up Galaxy startup time by disabling index of help,
        # not needed on production systems but useful if running many functional tests.
        self.index_tool_help = string_as_bool( kwargs.get( "index_tool_help", True ) )
        # Location for tool dependencies.
        if 'tool_dependency_dir' in kwargs:
            self.tool_dependency_dir = resolve_path( kwargs.get( "tool_dependency_dir" ), self.root )
            # Setting the following flag to true will ultimately cause tool dependencies
            # to be located in the shell environment and used by the job that is executing
            # the tool.
            self.use_tool_dependencies = True
        else:
            self.tool_dependency_dir = None
            self.use_tool_dependencies = False
        # Configuration options for taking advantage of nginx features
        self.upstream_gzip = string_as_bool( kwargs.get( 'upstream_gzip', False ) )
        self.apache_xsendfile = string_as_bool( kwargs.get( 'apache_xsendfile', False ) )
        self.nginx_x_accel_redirect_base = kwargs.get( 'nginx_x_accel_redirect_base', False )
        self.nginx_x_archive_files_base = kwargs.get( 'nginx_x_archive_files_base', False )
        self.nginx_upload_store = kwargs.get( 'nginx_upload_store', False )
        self.nginx_upload_path = kwargs.get( 'nginx_upload_path', False )
        if self.nginx_upload_store:
            self.nginx_upload_store = os.path.abspath( self.nginx_upload_store )
        self.object_store = kwargs.get( 'object_store', 'disk' )
        self.object_store_check_old_style = string_as_bool( kwargs.get( 'object_store_check_old_style', False ) )
        self.object_store_cache_path = resolve_path( kwargs.get( "object_store_cache_path", "database/object_store_cache" ), self.root )
        # Handle AWS-specific config options for backward compatibility
        if kwargs.get( 'aws_access_key', None) is not None:
            self.os_access_key = kwargs.get( 'aws_access_key', None )
            self.os_secret_key = kwargs.get( 'aws_secret_key', None )
            self.os_bucket_name = kwargs.get( 's3_bucket', None )
            self.os_use_reduced_redundancy = kwargs.get( 'use_reduced_redundancy', False )
        else:
            self.os_access_key = kwargs.get( 'os_access_key', None )
            self.os_secret_key = kwargs.get( 'os_secret_key', None )
            self.os_bucket_name = kwargs.get( 'os_bucket_name', None )
            self.os_use_reduced_redundancy = kwargs.get( 'os_use_reduced_redundancy', False )
        self.os_host = kwargs.get( 'os_host', None )
        self.os_port = kwargs.get( 'os_port', None )
        self.os_is_secure = string_as_bool( kwargs.get( 'os_is_secure', True ) )
        self.os_conn_path = kwargs.get( 'os_conn_path', '/' )
        self.object_store_cache_size = float(kwargs.get( 'object_store_cache_size', -1 ))
        self.distributed_object_store_config_file = kwargs.get( 'distributed_object_store_config_file', None )
        if self.distributed_object_store_config_file is not None:
            self.distributed_object_store_config_file = resolve_path( self.distributed_object_store_config_file, self.root )
        self.irods_root_collection_path = kwargs.get( 'irods_root_collection_path', None )
        self.irods_default_resource = kwargs.get( 'irods_default_resource', None )
        # Parse global_conf and save the parser
        global_conf = kwargs.get( 'global_conf', None )
        global_conf_parser = ConfigParser.ConfigParser()
        self.config_file = None
        self.global_conf_parser = global_conf_parser
        if global_conf and "__file__" in global_conf:
            self.config_file = global_conf['__file__']
            global_conf_parser.read(global_conf['__file__'])
        # Heartbeat log file name override
        if global_conf is not None:
            self.heartbeat_log = global_conf.get( 'heartbeat_log', 'heartbeat.log' )
        # Determine which 'server:' this is
        self.server_name = 'main'
        for arg in sys.argv:
            # Crummy, but PasteScript does not give you a way to determine this
            if arg.lower().startswith('--server-name='):
                self.server_name = arg.split('=', 1)[-1]
        # Allow explicit override of server name in confg params
        if "server_name" in kwargs:
            self.server_name = kwargs.get("server_name")
        # Store all configured server names
        self.server_names = []
        for section in global_conf_parser.sections():
            if section.startswith('server:'):
                self.server_names.append(section.replace('server:', '', 1))

        # Default URL (with schema http/https) of the Galaxy instance within the
        # local network - used to remotely communicate with the Galaxy API.
        galaxy_infrastructure_url = kwargs.get( 'galaxy_infrastructure_url', None )
        galaxy_infrastructure_url_set = True
        if galaxy_infrastructure_url is None:
            # Still provide a default but indicate it was not explicitly set
            # so dependending on the context a better default can be used (
            # request url in a web thread, Docker parent in IE stuff, etc...)
            galaxy_infrastructure_url = "http://localhost"
            port = self.guess_galaxy_port()
            if port:
                galaxy_infrastructure_url += ":%s" % (port)
            galaxy_infrastructure_url_set = False
        if "HOST_IP" in galaxy_infrastructure_url:
            galaxy_infrastructure_url = string.Template(galaxy_infrastructure_url).safe_substitute({
                'HOST_IP': socket.gethostbyname(socket.gethostname())
            })
        self.galaxy_infrastructure_url = galaxy_infrastructure_url
        self.galaxy_infrastructure_url_set = galaxy_infrastructure_url_set

        # Store advanced job management config
        self.job_manager = kwargs.get('job_manager', self.server_name).strip()
        self.job_handlers = [ x.strip() for x in kwargs.get('job_handlers', self.server_name).split(',') ]
        self.default_job_handlers = [ x.strip() for x in kwargs.get('default_job_handlers', ','.join( self.job_handlers ) ).split(',') ]
        # Use database for job running IPC unless this is a standalone server or explicitly set in the config
        if self.track_jobs_in_database == 'None':
            self.track_jobs_in_database = False
            if len(self.server_names) > 1:
                self.track_jobs_in_database = True
        else:
            self.track_jobs_in_database = string_as_bool( self.track_jobs_in_database )
        # Store per-tool runner configs
        self.tool_handlers = self.__read_tool_job_config( global_conf_parser, 'galaxy:tool_handlers', 'name' )
        self.tool_runners = self.__read_tool_job_config( global_conf_parser, 'galaxy:tool_runners', 'url' )
        # Cloud configuration options
        self.enable_cloud_launch = string_as_bool( kwargs.get( 'enable_cloud_launch', False ) )
        self.cloudlaunch_default_ami = kwargs.get( 'cloudlaunch_default_ami', 'ami-a7dbf6ce' )
        # Galaxy messaging (AMQP) configuration options
        self.amqp = {}
        try:
            amqp_config = global_conf_parser.items("galaxy_amqp")
        except ConfigParser.NoSectionError:
            amqp_config = {}
        for k, v in amqp_config:
            self.amqp[k] = v
        # Galaxy internal control queue configuration.
        # If specified in universe, use it, otherwise we use whatever 'real'
        # database is specified.  Lastly, we create and use new sqlite database
        # (to minimize locking) as a final option.
        if 'amqp_internal_connection' in kwargs:
            self.amqp_internal_connection = kwargs.get('amqp_internal_connection')
            # TODO Get extra amqp args as necessary for ssl
        elif 'database_connection' in kwargs:
            self.amqp_internal_connection = "sqlalchemy+" + self.database_connection
        else:
            self.amqp_internal_connection = "sqlalchemy+sqlite:///%s?isolation_level=IMMEDIATE" % resolve_path( "database/control.sqlite", self.root )
        self.biostar_url = kwargs.get( 'biostar_url', None )
        self.biostar_key_name = kwargs.get( 'biostar_key_name', None )
        self.biostar_key = kwargs.get( 'biostar_key', None )
        self.biostar_enable_bug_reports = string_as_bool( kwargs.get( 'biostar_enable_bug_reports', True ) )
        self.biostar_never_authenticate = string_as_bool( kwargs.get( 'biostar_never_authenticate', False ) )
        self.pretty_datetime_format = expand_pretty_datetime_format( kwargs.get( 'pretty_datetime_format', '$locale (UTC)' ) )
        self.master_api_key = kwargs.get( 'master_api_key', None )
        if self.master_api_key == "changethis":  # default in sample config file
            raise Exception("Insecure configuration, please change master_api_key to something other than default (changethis)")

        # Experimental: This will not be enabled by default and will hide
        # nonproduction code.
        # The api_folders refers to whether the API exposes the /folders section.
        self.api_folders = string_as_bool( kwargs.get( 'api_folders', False ) )
        # This is for testing new library browsing capabilities.
        self.new_lib_browse = string_as_bool( kwargs.get( 'new_lib_browse', False ) )
        # Error logging with sentry
        self.sentry_dsn = kwargs.get( 'sentry_dsn', None )
        # Logging with fluentd
        self.fluent_log = string_as_bool( kwargs.get( 'fluent_log', False ) )
        self.fluent_host = kwargs.get( 'fluent_host', 'localhost' )
        self.fluent_port = int( kwargs.get( 'fluent_port', 24224 ) )
        # directory where the visualization/registry searches for plugins
        self.visualization_plugins_directory = kwargs.get(
            'visualization_plugins_directory', 'config/plugins/visualizations' )
        ie_dirs = kwargs.get( 'interactive_environment_plugins_directory', None )
        if ie_dirs and not self.visualization_plugins_directory:
            self.visualization_plugins_directory = ie_dirs
        elif ie_dirs:
            self.visualization_plugins_directory += ",%s" % ie_dirs

        self.proxy_session_map = self.resolve_path( kwargs.get( "dynamic_proxy_session_map", "database/session_map.sqlite" ) )
        self.manage_dynamic_proxy = string_as_bool( kwargs.get( "dynamic_proxy_manage", "True" ) )  # Set to false if being launched externally
        self.dynamic_proxy_debug = string_as_bool( kwargs.get( "dynamic_proxy_debug", "False" ) )
        self.dynamic_proxy_bind_port = int( kwargs.get( "dynamic_proxy_bind_port", "8800" ) )
        self.dynamic_proxy_bind_ip = kwargs.get( "dynamic_proxy_bind_ip", "0.0.0.0" )
        self.dynamic_proxy_external_proxy = string_as_bool( kwargs.get( "dynamic_proxy_external_proxy", "False" ) )

        # Default chunk size for chunkable datatypes -- 64k
        self.display_chunk_size = int( kwargs.get( 'display_chunk_size', 65536) )

        self.citation_cache_type = kwargs.get( "citation_cache_type", "file" )
        self.citation_cache_data_dir = self.resolve_path( kwargs.get( "citation_cache_data_dir", "database/citations/data" ) )
        self.citation_cache_lock_dir = self.resolve_path( kwargs.get( "citation_cache_lock_dir", "database/citations/locks" ) )
        # TEST FOR UWSGI
        self.is_uwsgi = False
        try:
            # The uwsgi module is automatically injected by the parent uwsgi
            # process and only exists that way.  If anything works, this is a
            # uwsgi-managed process.
            import uwsgi
            if uwsgi.numproc:
                self.is_uwsgi = True
        except ImportError:
            # This is not a uwsgi process, or something went horribly wrong.
            pass

    @property
    def sentry_dsn_public( self ):
        """
        Sentry URL with private key removed for use in client side scripts,
        sentry server will need to be configured to accept events
        """
        if self.sentry_dsn:
            return re.sub( r"^([^:/?#]+:)?//(\w+):(\w+)", r"\1//\2", self.sentry_dsn )
        else:
            return None

    def __parse_config_file_options( self, kwargs ):
        """
        Backwards compatibility for config files moved to the config/ dir.
        """
        defaults = dict(
            data_manager_config_file=[ 'config/data_manager_conf.xml', 'data_manager_conf.xml', 'config/data_manager_conf.xml.sample' ],
            datatypes_config_file=[ 'config/datatypes_conf.xml', 'datatypes_conf.xml', 'config/datatypes_conf.xml.sample' ],
            external_service_type_config_file=[ 'config/external_service_types_conf.xml', 'external_service_types_conf.xml', 'config/external_service_types_conf.xml.sample' ],
            job_config_file=[ 'config/job_conf.xml', 'job_conf.xml' ],
            job_metrics_config_file=[ 'config/job_metrics_conf.xml', 'job_metrics_conf.xml' ],
            dependency_resolvers_config_file=[ 'config/dependency_resolvers_conf.xml', 'dependency_resolvers_conf.xml' ],
            job_resource_params_file=[ 'config/job_resource_params_conf.xml', 'job_resource_params_conf.xml' ],
            migrated_tools_config=[ 'migrated_tools_conf.xml', 'config/migrated_tools_conf.xml' ],
            object_store_config_file=[ 'config/object_store_conf.xml', 'object_store_conf.xml' ],
            openid_config_file=[ 'config/openid_conf.xml', 'openid_conf.xml', 'config/openid_conf.xml.sample' ],
            shed_data_manager_config_file=[ 'shed_data_manager_conf.xml', 'config/shed_data_manager_conf.xml' ],
            shed_tool_data_table_config=[ 'shed_tool_data_table_conf.xml', 'config/shed_tool_data_table_conf.xml' ],
            tool_sheds_config_file=[ 'config/tool_sheds_conf.xml', 'tool_sheds_conf.xml', 'config/tool_sheds_conf.xml.sample' ],
            workflow_schedulers_config_file=['config/workflow_schedulers_conf.xml', 'config/workflow_schedulers_conf.xml.sample'],
        )

        listify_defaults = dict(
            tool_data_table_config_path=[ 'config/tool_data_table_conf.xml', 'tool_data_table_conf.xml', 'config/tool_data_table_conf.xml.sample' ],
            # rationale:
            # [0]: user has explicitly created config/tool_conf.xml but did not
            #      move their existing shed_tool_conf.xml, don't use
            #      config/shed_tool_conf.xml, which is probably the empty
            #      version copied from the sample, or else their shed tools
            #      will disappear
            # [1]: user has created config/tool_conf.xml and, having passed
            #      [0], probably moved their shed_tool_conf.xml as well
            # [2]: user has done nothing, use the old files
            # [3]: fresh install
            tool_config_file=[ 'config/tool_conf.xml,shed_tool_conf.xml',
                               'config/tool_conf.xml,config/shed_tool_conf.xml',
                               'tool_conf.xml,shed_tool_conf.xml',
                               'config/tool_conf.xml.sample,config/shed_tool_conf.xml' ]
        )

        for var, defaults in defaults.items():
            if kwargs.get( var, None ) is not None:
                path = kwargs.get( var )
            else:
                for default in defaults:
                    if os.path.exists( resolve_path( default, self.root ) ):
                        path = default
                        break
                else:
                    path = defaults[-1]
            setattr( self, var, resolve_path( path, self.root ) )

        for var, defaults in listify_defaults.items():
            paths = []
            if kwargs.get( var, None ) is not None:
                paths = listify( kwargs.get( var ) )
            else:
                for default in defaults:
                    for path in listify( default ):
                        if not os.path.exists( resolve_path( path, self.root ) ):
                            break
                    else:
                        paths = listify( default )
                        break
                else:
                    paths = listify( defaults[-1] )
            setattr( self, var, [ resolve_path( x, self.root ) for x in paths ] )

        # Backwards compatibility for names used in too many places to fix
        self.datatypes_config = self.datatypes_config_file
        self.tool_configs = self.tool_config_file

    def __read_tool_job_config( self, global_conf_parser, section, key ):
        try:
            tool_runners_config = global_conf_parser.items( section )

            # Process config to group multiple configs for the same tool.
            rval = {}
            for entry in tool_runners_config:
                tool_config, val = entry
                tool = None
                runner_dict = {}
                if tool_config.find("[") != -1:
                    # Found tool with additional params; put params in dict.
                    tool, params = tool_config[:-1].split( "[" )
                    param_dict = {}
                    for param in params.split( "," ):
                        name, value = param.split( "@" )
                        param_dict[ name ] = value
                    runner_dict[ 'params' ] = param_dict
                else:
                    tool = tool_config

                # Add runner URL.
                runner_dict[ key ] = val

                # Create tool entry if necessary.
                if tool not in rval:
                    rval[ tool ] = []

                # Add entry to runners.
                rval[ tool ].append( runner_dict )

            return rval
        except ConfigParser.NoSectionError:
            return {}

    def get( self, key, default ):
        return self.config_dict.get( key, default )

    def get_bool( self, key, default ):
        if key in self.config_dict:
            return string_as_bool( self.config_dict[key] )
        else:
            return default

    def ensure_tempdir( self ):
        self._ensure_directory( self.new_file_path )

    def _ensure_directory( self, path ):
        if path not in [ None, False ] and not os.path.isdir( path ):
            try:
                os.makedirs( path )
            except Exception, e:
                raise ConfigurationError( "Unable to create missing directory: %s\n%s" % ( path, e ) )

    def check( self ):
        paths_to_check = [ self.root, self.tool_path, self.tool_data_path, self.template_path ]
        # Check that required directories exist
        for path in paths_to_check:
            if path not in [ None, False ] and not os.path.isdir( path ):
                try:
                    os.makedirs( path )
                except Exception, e:
                    raise ConfigurationError( "Unable to create missing directory: %s\n%s" % ( path, e ) )
        # Create the directories that it makes sense to create
        if self.object_store_config_file is None:
            for path in (self.file_path, self.job_working_directory):
                self._ensure_directory( path )
        for path in (self.new_file_path, self.template_cache, self.ftp_upload_dir,
                     self.library_import_dir, self.user_library_import_dir,
                     self.nginx_upload_store, self.whoosh_index_dir,
                     self.object_store_cache_path):
            self._ensure_directory( path )
        # Check that required files exist
        tool_configs = self.tool_configs
        if self.migrated_tools_config not in tool_configs:
            tool_configs.append( self.migrated_tools_config )
        for path in tool_configs:
            if not os.path.exists( path ):
                raise ConfigurationError("Tool config file not found: %s" % path )
        for datatypes_config in listify( self.datatypes_config ):
            if not os.path.isfile( datatypes_config ):
                raise ConfigurationError("Datatypes config file not found: %s" % datatypes_config )
        # Check for deprecated options.
        for key in self.config_dict.keys():
            if key in self.deprecated_options:
                log.warning( "Config option '%s' is deprecated and will be removed in a future release.  Please consult the latest version of the sample configuration file." % key )

    def is_admin_user( self, user ):
        """
        Determine if the provided user is listed in `admin_users`.

        NOTE: This is temporary, admin users will likely be specified in the
              database in the future.
        """
        admin_users = [ x.strip() for x in self.get( "admin_users", "" ).split( "," ) ]
        return ( user is not None and user.email in admin_users )

    def resolve_path( self, path ):
        """ Resolve a path relative to Galaxy's root.
        """
        return resolve_path( path, self.root )

    def guess_galaxy_port(self):
        # Code derived from IPython work ie.mako
        config = ConfigParser.SafeConfigParser({'port': '8080'})
        if self.config_file:
            config.read( self.config_file )

        try:
            port = config.getint('server:%s' % self.server_name, 'port')
        except:
            # uWSGI galaxy installations don't use paster and only speak uWSGI not http
            port = None
        return port


def get_database_engine_options( kwargs, model_prefix='' ):
    """
    Allow options for the SQLAlchemy database engine to be passed by using
    the prefix "database_engine_option".
    """
    conversions = {
        'convert_unicode': string_as_bool,
        'pool_timeout': int,
        'echo': string_as_bool,
        'echo_pool': string_as_bool,
        'pool_recycle': int,
        'pool_size': int,
        'max_overflow': int,
        'pool_threadlocal': string_as_bool,
        'server_side_cursors': string_as_bool
    }
    prefix = "%sdatabase_engine_option_" % model_prefix
    prefix_len = len( prefix )
    rval = {}
    for key, value in kwargs.iteritems():
        if key.startswith( prefix ):
            key = key[prefix_len:]
            if key in conversions:
                value = conversions[key](value)
            rval[ key  ] = value
    return rval


def configure_logging( config ):
    """
    Allow some basic logging configuration to be read from ini file.
    """
    # Get root logger
    root = logging.getLogger()
    # PasteScript will have already configured the logger if the
    # 'loggers' section was found in the config file, otherwise we do
    # some simple setup using the 'log_*' values from the config.
    if not config.global_conf_parser.has_section( "loggers" ):
        format = config.get( "log_format", "%(name)s %(levelname)s %(asctime)s %(message)s" )
        level = logging._levelNames[ config.get( "log_level", "DEBUG" ) ]
        destination = config.get( "log_destination", "stdout" )
        log.info( "Logging at '%s' level to '%s'" % ( level, destination ) )
        # Set level
        root.setLevel( level )
        # Turn down paste httpserver logging
        if level <= logging.DEBUG:
            logging.getLogger( "paste.httpserver.ThreadPool" ).setLevel( logging.WARN )
        # Remove old handlers
        for h in root.handlers[:]:
            root.removeHandler(h)
        # Create handler
        if destination == "stdout":
            handler = logging.StreamHandler( sys.stdout )
        else:
            handler = logging.FileHandler( destination )
        # Create formatter
        formatter = logging.Formatter( format )
        # Hook everything up
        handler.setFormatter( formatter )
        root.addHandler( handler )
    # If sentry is configured, also log to it
    if config.sentry_dsn:
        eggs.require( "raven" )
        from raven.handlers.logging import SentryHandler
        sentry_handler = SentryHandler( config.sentry_dsn )
        sentry_handler.setLevel( logging.WARN )
        root.addHandler( sentry_handler )


class ConfiguresGalaxyMixin:
    """ Shared code for configuring Galaxy-like app objects.
    """

    def _configure_genome_builds( self, data_table_name="__dbkeys__", load_old_style=True ):
        self.genome_builds = GenomeBuilds( self, data_table_name=data_table_name, load_old_style=load_old_style )

    def _configure_toolbox( self ):
        # Initialize the tools, making sure the list of tool configs includes the reserved migrated_tools_conf.xml file.
        tool_configs = self.config.tool_configs
        if self.config.migrated_tools_config not in tool_configs:
            tool_configs.append( self.config.migrated_tools_config )

        from galaxy.managers.citations import CitationsManager
        self.citations_manager = CitationsManager( self )

        from galaxy import tools
        self.toolbox = tools.ToolBox( tool_configs, self.config.tool_path, self )
        self.reindex_tool_search()

        from galaxy.tools.deps import containers
        galaxy_root_dir = os.path.abspath(self.config.root)
        file_path = os.path.abspath(getattr(self.config, "file_path"))
        app_info = containers.AppInfo(
            galaxy_root_dir,
            default_file_path=file_path,
            outputs_to_working_directory=self.config.outputs_to_working_directory,
            container_image_cache_path=self.config.container_image_cache_path,
        )
        self.container_finder = containers.ContainerFinder(app_info)

    def reindex_tool_search( self ):
        # Call this when tools are added or removed.
        import galaxy.tools.search
        index_help = getattr( self.config, "index_tool_help", True )
        self.toolbox_search = galaxy.tools.search.ToolBoxSearch( self.toolbox, index_help )

    def _configure_tool_data_tables( self, from_shed_config ):
        from galaxy.tools.data import ToolDataTableManager

        # Initialize tool data tables using the config defined by self.config.tool_data_table_config_path.
        self.tool_data_tables = ToolDataTableManager( tool_data_path=self.config.tool_data_path,
                                                      config_filename=self.config.tool_data_table_config_path )
        # Load additional entries defined by self.config.shed_tool_data_table_config into tool data tables.
        self.tool_data_tables.load_from_config_file( config_filename=self.config.shed_tool_data_table_config,
                                                     tool_data_path=self.tool_data_tables.tool_data_path,
                                                     from_shed_config=from_shed_config )

    def _configure_datatypes_registry( self, installed_repository_manager=None ):
        from galaxy.datatypes import registry
        # Create an empty datatypes registry.
        self.datatypes_registry = registry.Registry()
        if installed_repository_manager:
            # Load proprietary datatypes defined in datatypes_conf.xml files in all installed tool shed repositories.  We
            # load proprietary datatypes before datatypes in the distribution because Galaxy's default sniffers include some
            # generic sniffers (eg text,xml) which catch anything, so it's impossible for proprietary sniffers to be used.
            # However, if there is a conflict (2 datatypes with the same extension) between a proprietary datatype and a datatype
            # in the Galaxy distribution, the datatype in the Galaxy distribution will take precedence.  If there is a conflict
            # between 2 proprietary datatypes, the datatype from the repository that was installed earliest will take precedence.
            installed_repository_manager.load_proprietary_datatypes()
        # Load the data types in the Galaxy distribution, which are defined in self.config.datatypes_config.
        datatypes_configs = self.config.datatypes_config
        for datatypes_config in listify( datatypes_configs ):
            # Setting override=False would make earlier files would take
            # precedence - but then they wouldn't override tool shed
            # datatypes.
            self.datatypes_registry.load_datatypes( self.config.root, datatypes_config, override=True )

    def _configure_object_store( self, **kwds ):
        from galaxy.objectstore import build_object_store_from_config
        self.object_store = build_object_store_from_config( self.config, **kwds )

    def _configure_security( self ):
        from galaxy.web import security
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )

    def _configure_tool_shed_registry( self ):
        import tool_shed.tool_shed_registry

        # Set up the tool sheds registry
        if os.path.isfile( self.config.tool_sheds_config_file ):
            self.tool_shed_registry = tool_shed.tool_shed_registry.Registry( self.config.root, self.config.tool_sheds_config_file )
        else:
            self.tool_shed_registry = None

    def _configure_models( self, check_migrate_databases=False, check_migrate_tools=False, config_file=None ):
        """
        Preconditions: object_store must be set on self.
        """
        if self.config.database_connection:
            db_url = self.config.database_connection
        else:
            db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % self.config.database
        install_db_url = self.config.install_database_connection
        # TODO: Consider more aggressive check here that this is not the same
        # database file under the hood.
        combined_install_database = not( install_db_url and install_db_url != db_url )
        install_db_url = install_db_url or db_url

        if check_migrate_databases:
            # Initialize database / check for appropriate schema version.  # If this
            # is a new installation, we'll restrict the tool migration messaging.
            from galaxy.model.migrate.check import create_or_verify_database
            create_or_verify_database( db_url, config_file, self.config.database_engine_options, app=self )
            if not combined_install_database:
                from galaxy.model.tool_shed_install.migrate.check import create_or_verify_database as tsi_create_or_verify_database
                tsi_create_or_verify_database( install_db_url, self.config.install_database_engine_options, app=self )

        if check_migrate_tools:
            # Alert the Galaxy admin to tools that have been moved from the distribution to the tool shed.
            from tool_shed.galaxy_install.migrate.check import verify_tools
            if combined_install_database:
                install_database_options = self.config.database_engine_options
            else:
                install_database_options = self.config.install_database_engine_options
            verify_tools( self, install_db_url, config_file, install_database_options )

        from galaxy.model import mapping
        self.model = mapping.init( self.config.file_path,
                                   db_url,
                                   self.config.database_engine_options,
                                   map_install_models=combined_install_database,
                                   database_query_profiling_proxy=self.config.database_query_profiling_proxy,
                                   object_store=self.object_store,
                                   trace_logger=getattr(self, "trace_logger", None),
                                   use_pbkdf2=self.config.get_bool( 'use_pbkdf2', True ) )

        if combined_install_database:
            log.info("Install database targetting Galaxy's database configuration.")
            self.install_model = self.model
        else:
            from galaxy.model.tool_shed_install import mapping as install_mapping
            install_db_url = self.config.install_database_connection
            log.info("Install database using its own connection %s" % install_db_url)
            install_db_engine_options = self.config.install_database_engine_options
            self.install_model = install_mapping.init( install_db_url,
                                                       install_db_engine_options )
