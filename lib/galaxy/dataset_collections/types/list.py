from ..types import BaseDatasetCollectionType

from galaxy.model import DatasetInstanceDatasetCollectionAssociation


class ListDatasetCollectionType( BaseDatasetCollectionType ):
    """ A flat list of named elements.
    """
    collection_type = "list"

    def __init__( self ):
        pass

    def build_collection( self, dataset_instances ):
        associations = []
        for identifier, dataset_instance in dataset_instances.iteritems():
            association = DatasetInstanceDatasetCollectionAssociation(
                dataset=dataset_instance,
                element_identifier=identifier,
            )
            associations.append( association )

        return self._new_collection_for_elements( associations )
