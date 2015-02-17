from galaxy.managers import base as manager_base


class LDDAManager( object ):
    """
    A fairly sparse manager for LDDAs.
    """

    def __init__( self, app ):
        """
        Set up and initialize other managers needed by lddas.
        """
        pass

    def get( self, trans, id, check_accessible=True ):
        return manager_base.get_object( trans, id,
                                        'LibraryDatasetDatasetAssociation',
                                        check_ownership=False,
                                        check_accessible=check_accessible )
