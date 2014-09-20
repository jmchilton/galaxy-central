from galaxy import util
from ..instrumenters import InstrumentPlugin
import json

import logging
log = logging.getLogger( __name__ )


class DockerMetricFormatter( object ):
    """ Format job metric key-value pairs for human consumption in Web UI. """

    def format( self, key, value ):
        key = "Docker Container Property | %s" % " | ".join( key.split("|") )
        if value == 0.0:
            value = "0"
        else:
            value = util.unicodify( value )
        return ( key, value )


class DockerContainerInfoPlugin( InstrumentPlugin ):
    """ Simple plugin that collects data without external dependencies. In
    particular it currently collects value set for Galaxy slots.
    """
    plugin_type = "docker"
    formatter = DockerMetricFormatter()

    def __init__( self, **kwargs ):
        pass

    def pre_execute_instrument( self, job_directory ):
        commands = []
        return commands

    def post_execute_instrument( self, job_directory ):
        commands = []
        return commands

    def docker_inspect_file( self, job_directory ):
        return self._instrument_file_path( job_directory, "inspect.json" )

    def job_properties( self, job_id, job_directory ):
        inspect_file = self.docker_inspect_file( job_directory )
        properties = {}
        with open( inspect_file, "r" ) as f:
            images_inspect_info = json.load( f )
            # inspect only given one argument - should just be one config dict
            image_inspect_info = images_inspect_info[ 0 ]
            _dump_to_simple_dict( image_inspect_info, properties )
        return properties


def _dump_to_simple_dict( image_inspect_info, properties, prefix="" ):
    """ Take nested json format dumped from Docker and convert it to a simple
    dictionary as required by job metrics infrastructure.
    """
    for key, value in image_inspect_info.items():
        if prefix:
            effective_key = "%s|%s" % ( prefix, key )
        else:
            effective_key = key

        if isinstance( value, dict ):
            _dump_to_simple_dict( value, properties, effective_key )
        else:
            if isinstance(value, list):
                # currently just command and environment so ; makes some sense
                value = ";".join(value)
            elif isinstance(value, bool) or value is None:
                value = str(value)
            properties[ effective_key ] = value

    return properties

__all__ = [ DockerContainerInfoPlugin ]
