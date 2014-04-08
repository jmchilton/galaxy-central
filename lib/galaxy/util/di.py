import inspect
from galaxy import util
from galaxy.util import submodules


def component( name=None ):
    def decorator( clazz ):
        component_name = name or util.inflector.underscore( clazz.__name__ )
        clazz._component_name = component_name
        return clazz

    return decorator


def object_graph( objects={}, modules=[], classes=[] ):
    all_objects = objects.copy()
    component_classes = classes[ : ]
    for module in modules:
        component_classes.extend( __module_components( module ) )

    __instantiate_classes( component_classes, all_objects )
    return all_objects


def instantiate_with_objects( clazz, objects ):
    dependencies = __class_dependencies( clazz )
    return __instantiate_class( clazz, dependencies, objects )


def __instantiate_classes( component_classes, all_objects ):
    to_instantiate = component_classes[ : ]
    dependencies = {}
    for component_class in component_classes:
        dependencies[ component_class ] = __class_dependencies( component_class )

    while to_instantiate:
        instantiated_this_iteration = {}
        to_remove = []

        for component_class in to_instantiate:
            component_dependencies = dependencies[ component_class ]
            if component_dependencies.issubset( all_objects.keys() ):
                component = __instantiate_class( component_class, component_dependencies, all_objects )
                instantiated_this_iteration[ component_class._component_name ] = component
                to_remove.append( component_class )
        if not instantiated_this_iteration:
            raise Exception( "Exception initialization object graph - following components have unmet dependencies %s" % to_instantiate )
        all_objects.update( instantiated_this_iteration )
        for component_class in to_remove:
            to_instantiate.remove( component_class )


def __instantiate_class( component_class, dependencies, objects ):
    kwargs = dict( [ ( d, objects[ d ] ) for d in dependencies ] )
    return component_class( **kwargs )


def __class_dependencies( clazz ):
    init_func = clazz.__init__
    if init_func is object.__init__:
        return set()
    else:
        return set( inspect.getargspec( clazz.__init__ ).args[ 1: ] )


def __module_components( module ):
    component_classes = set()
    for submodule in submodules.submodules( module ):
        for name, clazz in inspect.getmembers( submodule, inspect.isclass ):
            if hasattr( clazz, "_component_name" ):
                component_classes.add( clazz )

    return component_classes
