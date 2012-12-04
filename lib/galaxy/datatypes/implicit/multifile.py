
from galaxy.datatypes.data import CompositeMultifile


class CompositeMultifileDatatypeLoader(object):
    """
    This class is responsible CompositeMultifile variants of all explicitly
    defined datatypes.
    """
    def __init__(self, registry):
        self.registry = registry

    def load(self):
        """
        Actually perform building and registering of composite datatypes.
        """
        datatypes_by_extension = self.registry.datatypes_by_extension
        for extension, datatype in dict(datatypes_by_extension).iteritems():
            multitype_extension = CompositeMultifile.build_multifile_extension(extension)
            if multitype_extension not in datatypes_by_extension:
                multi_datatype = self.__build_multi_datatype(extension, datatype)
                self.__add(multitype_extension, multi_datatype)

    def __build_multi_datatype(self, extension, datatype):
        multi_datatype_class = type("CompositeMultifileForExt%s" % extension, (CompositeMultifile,), {})
        multi_datatype_class.copy_metadata_spec(datatype.__class__)
        multi_datatype = multi_datatype_class(singleton_type=datatype)
        return multi_datatype

    def __add(self, multitype_extension, multi_datatype):
        self.registry.datatypes_by_extension[multitype_extension] = multi_datatype
        self.registry.mimetypes_by_extension[multitype_extension] = multi_datatype.get_mime()
