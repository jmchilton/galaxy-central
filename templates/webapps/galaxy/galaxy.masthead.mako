<%namespace file="/galaxy_client_app.mako" import="get_user_dict" />

## masthead head generator
<%def name="load(active_view = None)">
    <%
        from markupsafe import escape
        ## get configuration
        masthead_config = {
            ## inject configuration
            'brand'                     : app.config.get("brand", ""),
            'nginx_upload_path'         : app.config.get("nginx_upload_path", h.url_for(controller='api', action='tools')),
            'use_remote_user'           : app.config.use_remote_user,
            'remote_user_logout_href'   : app.config.remote_user_logout_href,
            'enable_cloud_launch'       : app.config.get_bool('enable_cloud_launch', False),
            'lims_doc_url'              : app.config.get("lims_doc_url", "http://main.g2.bx.psu.edu/u/rkchak/p/sts"),
            'biostar_url'               : app.config.biostar_url,
            'biostar_url_redirect'      : h.url_for( controller='biostar', action='biostar_redirect', qualified=True ),
            'support_url'               : app.config.get("support_url", "http://wiki.galaxyproject.org/Support"),
            'search_url'                : app.config.get("search_url", "http://galaxyproject.org/search/usegalaxy/"),
            'mailing_lists'             : app.config.get("mailing_lists", "http://wiki.galaxyproject.org/MailingLists"),
            'screencasts_url'           : app.config.get("screencasts_url", "http://vimeo.com/galaxyproject"),
            'wiki_url'                  : app.config.get("wiki_url", "http://galaxyproject.org/"),
            'citation_url'              : app.config.get("citation_url", "http://wiki.galaxyproject.org/CitingGalaxy"),
            'terms_url'                 : app.config.get("terms_url", ""),
            'allow_user_creation'       : app.config.allow_user_creation,
            'logo_url'                  : h.url_for(app.config.get( 'logo_url', '/')),
            'is_admin_user'             : trans.user_is_admin(),
            'active_view'               : active_view,
            'ftp_upload_dir'            : app.config.get("ftp_upload_dir",  None),
            'ftp_upload_site'           : app.config.get("ftp_upload_site",  None),
            'datatypes_disable_auto'    : app.config.get_bool("datatypes_disable_auto",  False),

            ## user details
            'user'          : {
                'requests'  : bool(trans.user and (trans.user.requests or trans.app.security_agent.get_accessible_request_types(trans, trans.user))),
                'email'     : escape( trans.user.email ) if (trans.user) else "",
                'valid'     : bool(trans.user != None),
                'json'      : get_user_dict()
            }
        }
    %>

    ## load the frame manager
    <script type="text/javascript">
        if( !window.Galaxy ){
            Galaxy = {};
        }

        ## load additional style sheet
        if (window != window.top){
            $('<link href="' + galaxy_config.root + 'static/style/galaxy.frame.masthead.css" rel="stylesheet">')
                .appendTo('head');
        }

        ## load galaxy js-modules
        require([
            'galaxy.masthead', 'galaxy.menu', 'mvc/ui/ui-modal', 'galaxy.frame', 'mvc/upload/upload-view',
            'mvc/user/user-model',
            'mvc/user/user-quotameter'
        ], function( mod_masthead, mod_menu, mod_modal, mod_frame, GalaxyUpload, user, quotameter ){
            if( !Galaxy.currUser ){
                // this doesn't need to wait for the page being readied
                Galaxy.currUser = new user.User(${ h.dumps( masthead_config[ 'user' ][ 'json' ], indent=2 ) });
            }

            $(function() {
                // check if masthead is available
                if (Galaxy.masthead){
                    return;
                }

                // get configuration
                var masthead_config = ${ h.dumps( masthead_config ) };

                // load global galaxy objects
                Galaxy.masthead = new mod_masthead.GalaxyMasthead(masthead_config);
                Galaxy.modal = new mod_modal.View();
                Galaxy.frame = new mod_frame.GalaxyFrame();

                // construct default menu options
                Galaxy.menu = new mod_menu.GalaxyMenu({
                    masthead: Galaxy.masthead,
                    config: masthead_config
                });
                
                // add upload plugin
                Galaxy.upload = new GalaxyUpload(masthead_config);

                // set up the quota meter (And fetch the current user data from trans)
                // add quota meter to masthead
                Galaxy.quotaMeter = new quotameter.UserQuotaMeter({
                    model   : Galaxy.currUser,
                    el      : Galaxy.masthead.$('.quota-meter-container')
                }).render();
            });
        });
    </script>
</%def>
