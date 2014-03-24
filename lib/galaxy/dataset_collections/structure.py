""" Module for reasoning about structure of and matching hierarchical collections of data.
"""
from galaxy.util import odict

import logging
log = logging.getLogger( __name__ )


class Leaf( object ):

    def __len__( self ):
        return 1

    @property
    def is_leaf( self ):
        return True

leaf = Leaf()


class Tree( object ):

    def __init__( self, dataset_collection, subcollection_type ):
        self.collection_type = dataset_collection.collection_type
        self.subcollection_type = subcollection_type
        children = []
        for element in dataset_collection.elements:
            child_collection = element.child_collection
            if child_collection:
                if child_collection.collection_type == subcollection_type:
                    children.append( ( element.element_identifier, leaf  ) )
                else:
                    children.append( ( element.element_identifier, Tree( child_collection, subcollection_type=subcollection_type )  ) )
            elif element.hda:
                children.append( ( element.element_identifier, leaf ) )

        self.children = children

    @property
    def is_leaf( self ):
        return False

    def can_match( self, other_structure ):
        if self.collection_type != other_structure.collection_type:
            # TODO: generalize
            return False

        if len( self.children ) != len( other_structure.children ):
            return False

        for my_child, other_child in zip( self.children, other_structure.children ):
            if my_child[ 0 ] != other_child[ 0 ]:  # Different identifiers, TODO: generalize
                return False

            # At least one is nested collection...
            if my_child[ 1 ].is_leaf != other_child[ 1 ].is_leaf:
                return False

            if not my_child[ 1 ].is_leaf and not my_child[ 1 ].can_match( other_child[ 1 ]):
                return False

        return True

    def __len__( self ):
        return sum( [ len( c[ 1 ] ) for c in self.children ] )

    def element_identifiers_for_datasets( self, trans, datasets ):
        element_identifiers = odict.odict()
        for identifier, child in self.children:
            if isinstance( child, Tree ):
                element_identifiers[ identifier ] = child.element_identifiers_for_datasets( trans, datasets[ 0:len( child ) ] )
            else:
                element_identifiers[ identifier ] = dict( src="hda", id=trans.security.encode_id( datasets[ 0 ].id ) )
            datasets = datasets[ len( child ): ]

        return dict(
            src="new_collection",
            collection_type=self.collection_type,
            element_identifiers=element_identifiers,
        )


def get_structure( dataset_collection_instance, subcollection_type=None ):
    return Tree( dataset_collection_instance.collection, subcollection_type=subcollection_type )
