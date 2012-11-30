
from galaxy.datatypes.data import CompositeMultifile

class CompositeMultifileDatatypeLoader( object ):
    
    def __init__(self, registry):
        self.registry = registry

    def load(self):
        datatypes_by_extension = self.registry.datatypes_by_extension
        for extension, datatype in dict(datatypes_by_extension).iteritems():
            multitype_extension = CompositeMultifile.build_multifile_extension(extension)
            if multitype_extension not in datatypes_by_extension:               
                multi_datatype = self._build_multi_datatype(extension, datatype)
                self._add(multitype_extension, multi_datatype)

    def _build_multi_datatype(self, extension, datatype):
        multi_datatype = CompositeMultifile(datatype)
        return multi_datatype

    def _add(self, multitype_extension, multi_datatype):
        self.registry.datatypes_by_extension[multitype_extension] = multi_datatype
        self.registry.mimetypes_by_extension[multitype_extension] = multi_datatype.get_mime()

                                                            

