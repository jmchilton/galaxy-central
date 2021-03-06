"""
Classes encapsulating galaxy tools and tool configuration.
"""

import logging, os, string, sys
from cookbook.odict import odict
from cookbook.patterns import Bunch
from galaxy import util, jobs
from elementtree import ElementTree
from parameters import *
from galaxy.tools.test import ToolTestBuilder

log = logging.getLogger( __name__ )

class ToolNotFoundException( Exception ):
    pass

class ToolBox( object ):
    """
    Container for a collection of tools
    """

    def __init__( self, config_filename, tool_root_dir ):
        """Create a toolbox from config in 'fname'"""
        self.tools_by_id = {}
        self.tools_and_sections_by_id = {}
        self.sections = []
        self.tool_root_dir = tool_root_dir
        try:
            self.init_tools( config_filename )
        except:
            log.exception( "ToolBox error reading %s", config_filename )

    def init_tools( self, config_filename ):
        """Reads the individual tool configurations paths from the main configuration file"""
        log.info("parsing the tool configuration")
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        for elem in root.findall("section"):
            section = ToolSection(elem)
            log.debug( "Loading tools in section: %s" % section.name )
            for tool in elem.findall("tool"):
                try:
                    path = tool.get("file")
                    tool = Tool( os.path.join( self.tool_root_dir, path ) )
                    log.debug( "Loaded tool: %s", tool.id )
                    self.tools_by_id[tool.id] = tool
                    self.tools_and_sections_by_id[tool.id] = tool, section
                    section.tools.append(tool)
                except Exception, exc:
                    log.exception( "error reading tool from path: %s" % path )
            self.sections.append(section)
        
    def reload( self, tool_id ):
        """
        Attempt to reload the tool identified by 'tool_id', if successfull 
        replace the old tool.
        """
        if tool_id not in self.tools_and_sections_by_id:
            raise ToolNotFoundException( "No tool with id %s" % tool_id )
        old_tool, section = self.tools_and_sections_by_id[ tool_id ]
        new_tool = Tool( old_tool.config_file )
        log.debug( "Reloaded tool %s", old_tool.id )
        # Is there a potential sync problem here? This should be roughly 
        # atomic. Too many indexes for tools...
        section.tools[ section.tools.index( old_tool ) ] = new_tool
        self.tools_by_id[ tool_id ] = new_tool
        self.tools_and_sections_by_id[ tool_id ] = new_tool, section
        
    def itertools( self ):
        """Return any tests associated with tools"""
        for section in self.sections:
            for tool in section.tools:
                yield tool

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.tools_by_id)

class ToolSection( object ):
    """A group of tools with similar type/purpose"""

    def __init__( self, elem):
        """Creates a tool section"""
        self.name = elem.get("name")
        self.id   = elem.get("id")
        self.tools = []

    def __str__( self ):
        return "%s: %s (%s)" % (self.__class__.__name__ , self.name, self.id) 

class DefaultToolState( object ):
    def __init__( self ):
        self.page = 0
        self.params = {}

class Tool:
    """
    Creates a tool class from a tool specification
    """
    def __init__( self, config_file ):
        """
        Load a tool from 'config file'
        """
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        # Parse XML configuration file and get the root element
        tree  = util.parse_xml( self.config_file )
        root  = tree.getroot()
        # Get the (user visible) name of the tool
        self.name = root.get("name")
        if not self.name: raise Exception, "Missing tool 'name'"
        # Get the UNIQUE id for the tool 
        # TODO: can this be generated automatically?
        self.id   = root.get("id")
        if not self.id: raise Exception, "Missing tool 'id'" 
        # Command line (template). Optional for tools that do not invoke a 
        # local program  
        command = root.find("command")
        if command is not None:
            self.command = util.xml_text(root, "command") # get rid of whitespace
            interpreter  = command.get("interpreter")
            if interpreter:
                self.command = interpreter + " " + os.path.join(self.tool_dir, self.command)
        else:
            self.command = ''
        # Short description of the tool
        self.description = util.xml_text(root, "description")
        # Load any tool specific code (optional)
        self.code_namespace = dict()
        for code_elem in root.findall("code"):
            file_name = code_elem.get("file")
            code_path = os.path.join( self.tool_dir, file_name )
            execfile( code_path, self.code_namespace )
        # Load parameters (optional)
        input_elem = root.find("inputs")
        if input_elem:
            # Handle properties of the input form
            self.check_values = util.string_as_bool( input_elem.get("check_values", "true") )
            self.action = input_elem.get( "action", "/tool_runner/index")
            self.target = input_elem.get( "target", "galaxy_main" )
            self.method = input_elem.get( "method", "post" )
            # Parse the actual parameters
            self.param_map = odict()
            self.param_map_by_page = list()
            self.display_by_page = list()
            enctypes = set()
            # Handle multiple page case
            pages = input_elem.findall( "page" )
            for page in ( pages or [ input_elem ] ):
                display, param_map = self.parse_page( page, enctypes )
                self.param_map_by_page.append( param_map )
                self.param_map.update( param_map )
                self.display_by_page.append( display )
            self.display = self.display_by_page[0]
            self.npages = len( self.param_map_by_page )
            self.last_page = len( self.param_map_by_page ) - 1
            self.has_multiple_pages = bool( self.last_page )
            # Determine the needed enctype for the form
            if len( enctypes ) == 0:
                self.enctype = "application/x-www-form-urlencoded"
            elif len( enctypes ) == 1:
                self.enctype = enctypes.pop()
            else:
                raise Exception, "Conflicting required enctypes: %s" % str( enctypes )
        # Check if the tool either has no parameters or only hidden (and
        # thus hardcoded) parameters. FIXME: hidden parameters aren't
        # parameters at all really, and should be passed in a different
        # way, making this check easier.
        self.input_required = False
        for param in self.param_map.values():
            if not isinstance( param, ( HiddenToolParameter, BaseURLToolParameter ) ):
                self.input_required = True
                break
        # Longer help text for the tool. Formatted in RST
        # TODO: Allow raw HTML or an external link.
        self.help = root.find("help")
        self.help_by_page = list()
        help_header = ""
        help_footer = ""
        if self.help is not None:
            help_pages = self.help.findall( "page" )
            help_header = self.help.text
            try:
                self.help = util.rst_to_html(self.help.text)
            except:
                log.exception( "error in help for tool %s" % self.name )
            # Multiple help page case
            if help_pages:
                for help_page in help_pages:
                    self.help_by_page.append( help_page.text )
                    help_footer = help_footer + help_page.tail
        # Each page has to rendered all-together because of backreferences allowed by rst
        try:
            self.help_by_page = [ \
                util.rst_to_html(help_header + x + help_footer) for x in self.help_by_page \
                ]
        except:
            log.exception( "error in multi-page help for tool %s" % self.name )
        # Pad out help pages to match npages ... could this be done better?
        while len(self.help_by_page) < self.npages: self.help_by_page.append( self.help )
        # FIXME: This is not used anywhere, what does it do?
        # url redirection to ougoings
        self.redir_url  = root.find("url")
        # Description of outputs produced by an invocation of the tool
        self.outputs = {}
        out_elem = root.find("outputs")
        if out_elem:
            for data_elem in out_elem.findall("data"):
                name = data_elem.get("name")
                format = data_elem.get("format", "data")
                metadata_source = data_elem.get("metadata_source", "")
                parent = data_elem.get("parent", None)
                self.outputs[name] = (format, metadata_source, parent) 
        # Action
        action_elem = root.find( "action" )
        if action_elem is None:
            self.tool_action = DefaultToolAction()
        else:
            module = action_elem.get( 'module' )
            cls = action_elem.get( 'class' )
            mod = __import__( module, globals(), locals(), [cls])
            self.tool_action = getattr( mod, cls )()
        # Tests
        tests_elem = root.find( "tests" )
        if tests_elem:
            try:
                self.parse_tests( tests_elem )
            except:
                log.exception( "Failed to parse tool tests" )
        else:
            self.tests = None
            
    def parse_tests( self, tests_elem ):
        """Parse any 'test' elements and save"""
        self.tests = []
        for i, test_elem in enumerate( tests_elem.findall( 'test' ) ):
            name = test_elem.get( 'name', 'Test-%d' % (i+1) )
            test = ToolTestBuilder( self, name )
            for param_elem in test_elem.findall( "param" ):
                attrib = dict( param_elem.attrib )
                if 'values' in attrib:
                    value = attrib[ 'values' ].split( ',' )
                elif 'value' in attrib:
                    value = attrib['value']
                else:
                    value = None
                test.add_param( attrib.pop( 'name' ), value, attrib )
            for output_elem in test_elem.findall( "output" ):
                attrib = dict( output_elem.attrib )
                test.add_output( attrib.pop( 'name' ), attrib.pop( 'file' ) )
            self.tests.append( test )

    def parse_page( self, input_elem, enctypes ):
        param_map = odict()
        for param_elem in input_elem.findall("param"):
            param = ToolParameter.build( self, param_elem )
            param_map[param.name] = param
            param_enctype = param.get_required_enctype()
            if param_enctype:
                enctypes.add( param_enctype )
        display_elem = input_elem.find("display")
        if display_elem is not None:
            display = util.xml_to_string(display_elem)
        else:
            display = None
        return display, param_map

    def get_param_html_map( self, trans, page=0 ):
        """Map containing HTML representation of each parameter"""
        return dict( ( key, param.get_html( trans ) ) for key, param in self.param_map_by_page[page].iteritems() )

    def get_param(self, key):
        """Returns a parameter by name"""
        return self.param_map.get(key, None)

    def __str__(self):
        return "%s: %s (%s)" % (self.__class__.__name__ , self.name, self.id)

    def get_hook(self, name):
        """Returns an externally loaded object from the namespace"""
        if self.code_namespace and name in self.code_namespace:
            return self.code_namespace[name]
        return None

    def handle_input( self, trans, incoming ):
        """Process incoming parameters for this tool"""
        # Get the state or create if not found
        if "tool_state" in incoming:
            state = util.string_to_object( incoming["tool_state"] )
        else:
            state = DefaultToolState()
            # This feels a bit like a hack
            if "runtool_btn" not in incoming and "URL" not in incoming:
                return "tool_form.tmpl", dict( errors={}, tool_state=state, param_values={}, incoming={} )
        # Check that values from previous page are all there
        params = dict()
        for p in range( state.page ):
            for param in self.param_map_by_page[p].values():
                if param.name in state.params:
                    params[param.name] = param.filter_value( state.params[ param.name ], trans, params )
                else:
                    raise Exception( "Value from previous page is not stored!" )
        # Now process new parameters for the current page
        error_map = dict()
        if self.check_values:
            # Validate each parameter
            for param in self.param_map_by_page[state.page].values():
                try:
                    value = orig_value = incoming.get( param.name, None )
                    if param.name == 'file_data':
                        value = orig_value
                    elif orig_value is not None or isinstance(param, DataToolParameter):
                        # Allow the value to be converted if neccesary
                        value = param.filter_value( orig_value, trans, params )
                        # Then do any further validation on the value
                        param.validate( value, trans.history )
                    # All okay, stuff it back into the parameter map
                    state.params[param.name] = orig_value
                    params[param.name] = value
                except ValueError, e:
                    error_map[param.name] = str( e )
            # Any tool specific validation
            validate_input = self.get_hook( 'validate_input' )
            if validate_input:
                validate_input( trans, error_map, params, self.param_map_by_page[state.page] )
        else:
            params = incoming
        
        #Add Tool Parameters to tool's namespace.
        self.code_namespace['GALAXY_TOOL_PARAMS']=Bunch(** params)
        
        # If there were errors, we stay on the same page and display 
        # error messages
        if error_map:
            error_message = "One or more errors were found in the input you provided. The specific errors are marked below."    
            return "tool_form.tmpl", dict( errors=error_map, tool_state=state, param_values=params, incoming=incoming, error_message=error_message )
        # If we've completed the last page we can execute the tool
        elif state.page == self.last_page:
            out_data = self.execute( trans, params )
            return 'tool_executed.tmpl', dict( out_data=out_data )
        # Otherwise move on to the next page
        else:
            state.page += 1
            return 'tool_form.tmpl', dict( errors={}, tool_state=state, param_values=params, incoming=incoming )
            
    def get_static_param_values( self, trans ):
        """
        Returns a map of parameter names and values if the tool does
        not require any user input. Will raise an exception if a
        parameter that does require input exists.
        """
        args = dict()
        for key, param in self.param_map.iteritems():
            if isinstance( param, HiddenToolParameter ):
                args[key] = param.value
            elif isinstance( param, BaseURLToolParameter ):
                args[key] = trans.request.base + param.value
            else:
                raise Exception( "Unexpected parameter type" )
        return args
            
    def execute( self, trans, incoming={} ):
        return self.tool_action.execute( self, trans, incoming )
        
    def params_to_strings( self, params, app ):
        rval = dict()
        for key, value in params.iteritems():
            if key in self.param_map:
                rval[ key ] = self.param_map[key].to_string( value, app )
            else:
                rval[ key ] = value
        return rval
        
    def params_to_python( self, params, app ):
        rval = dict()
        for key, value in params.iteritems():
            if key in self.param_map:
                rval[ key ] = self.param_map[key].to_python( value, app )
            else:
                rval[ key ] = value
        return rval

class ToolAction( object ):
    """
    The actions to be taken when a tool is run (after parameters have
    been converted and validated).
    """
    def execute( self, tool, trans, incoming={} ):
        raise TypeError("Abstract method")
    
class DefaultToolAction( object ):
    """
    Default tool action is to run an external command
    """
    def execute(self, tool, trans, incoming={} ):
        inp_data   = {}
        out_data   = {}
        # collect the input data
        for name, value in incoming.items():
            param = tool.get_param(name)
            if param:
                count = 1
                if isinstance(param, DataToolParameter ):
                    # multiple inputs on the same parameter name will be created as name1, name2 ...
                    if isinstance( value, list ):
                        for v in value:
                            inp_data[name+str(count)] = v 
                            count += 1
                    else:
                        inp_data[name] = value
        
        # input metadata
        input_names, input_ext, input_dbkey, input_meta = [ ], 'data', incoming.get("dbkey", "?"), Bunch()
        for name, data in inp_data.items():
            #fix for fake incoming data
            if data == None:
                data = trans.app.model.Dataset()
                data.state = data.states.FAKE
            input_names.append( 'data %s' % data.hid)
            input_ext   = data.ext
            if data.dbkey not in [None, '?']:
                input_dbkey = data.dbkey
            for meta_key, meta_value in data.metadata.items():
                if meta_value is not None:
                    meta_key = '%s_%s' % (name, meta_key)
                    incoming[meta_key] = meta_value

        # format input names  for display
        if input_names: 
            input_names = 'on ' + ', '.join(input_names)
        else:
            input_names = '' 
        
        # add the dbkey to the incoming parameters
        incoming["dbkey"] = input_dbkey
        
        #Use to store param_name -> data id and existing child/parent relationships
        name_id = {}
        child_parent = {}
        # create the output data
        for name, elems in tool.outputs.items():
            (ext, metadata_source, parent) = elems
            if parent:
                child_parent[name]=parent
            # hack! the output data has already been created
            if name in incoming:
                dataid = incoming[name]
                data = trans.app.model.Dataset.get( dataid )
                assert data != None
                out_data[name] = data
                continue 
            
            # the type should match the input
            if ext == "input":
                ext = input_ext
            
            trans.app.model.flush()
            data = trans.app.model.Dataset()
            # Commit immediately so it gets an id
            data.flush()
            
            #create an empty file
            open(data.file_name,"w").close()
            
            trans.app.model.flush()
            
            data.designation = name
            
            data.extension = ext
            if metadata_source:
                data.metadata = Bunch( ** inp_data[metadata_source].metadata.__dict__ )
            else:
                data.init_meta()

            data.dbkey = input_dbkey
            data.state = data.states.QUEUED
            data.blurb = "queued"
            data.name  = '%s %s' % (tool.name, input_names)
            out_data[name] = data
            trans.app.model.flush()
            name_id[name] = data.id
            
        #add parent datasets to history
        for name in out_data.keys():
            if name not in child_parent.keys():
                data = out_data[name]
                trans.history.add_dataset( data )
                data.flush()
        #add children datasets to history
        for name in out_data.keys():
            if name in child_parent.keys():
                data = out_data[name]
                data.parent_id = name_id[child_parent[name]]
                trans.history.add_dataset( data, parent_id=data.parent_id )
                data.flush()
        
        # custom pre-job setup
        try:
            # FIXME: this hook should probably be called exec_before_job_queued
            code = tool.get_hook( 'exec_before_job' )
            if code:
                code( trans, inp_data=inp_data, out_data=out_data, tool=tool, param_dict=incoming )
        except Exception, e:
            raise Exception, 'error in exec_before_job function %s' % e
        # store data after custom code runs 
        trans.app.model.flush()
        # Create the job object
        job = trans.app.model.Job()
        job.tool_id = tool.id
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )
        for name, dataset in inp_data.iteritems():
            job.add_input_dataset( name, dataset )
        for name, dataset in out_data.iteritems():
            job.add_output_dataset( name, dataset )
        trans.app.model.flush()
        # Build object for passing to job queue
        inp_data_ids = dict( ( key, d.id ) for ( key, d ) in inp_data.items() )
        out_data_ids = dict( ( key, d.id ) for ( key, d ) in out_data.items() )
        job = jobs.Job(trans, command=tool.command, inp_data_ids=inp_data_ids, 
                       out_data_ids=out_data_ids, incoming=incoming, tool=tool)
        trans.app.job_queue.put( job )
        return out_data
