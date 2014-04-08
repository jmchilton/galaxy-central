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
    for component_class in component_classes:
        dependencies = __class_dependencies( component_class )
        for dependency in dependencies:
            if dependency not in all_objects:
                __instantiate_classes( [ c for c in component_classes if c._component_name == dependency ], all_objects )
            component = __instantiate_class( component_class, dependencies, all_objects )
            all_objects[ component_class._component_name ] = component


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
