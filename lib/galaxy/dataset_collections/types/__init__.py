from abc import ABCMeta
from abc import abstractmethod

from galaxy import model


class DatasetCollectionType(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def build_collection(self, dataset_instances):
        """
        Build DatasetCollection with populated
        DatasetInstanceDatasetCollectionAssociations objects corresponding to
        the supplied dataset instances or throw exception if this is not a
        valid collection of the specified type.
        """


class BaseDatasetCollectionType(DatasetCollectionType):

    def _validation_failed(self, message):
        raise Exception(message)

    def _new_collection_for_elements(self, elements):
        dataset_collection = model.DatasetCollection(collection_type=self.collection_type)
        datasets = []
        for index, element in enumerate(elements):
            element.element_index = index
            element.collection = dataset_collection
            datasets.append(element)
        dataset_collection.datasets = datasets
        return dataset_collection
