"""
Many models in Galaxy are not meant to be removed from the database but only
marked as deleted. These models have the boolean attribute 'deleted'.

Other models are deletable and also may be purged. Most often these are
models have some backing/supporting resources that can be removed as well
(e.g. Datasets have data files on a drive). Purging these models removes
the supporting resources as well. These models also have the boolean
attribute 'purged'.
"""

# ---- Deletable and Purgable models
class DeletableManagerMixin( object ):
    """
    A mixin/interface for a model that is deletable (i.e. has a 'deleted' attr).

    Many resources in Galaxy can be marked as deleted - meaning (in most cases)
    that they are no longer needed, should not be displayed, or may be actually
    removed by an admin/script.
    """

    def delete( self, trans, item, flush=True, **kwargs ):
        """
        Mark as deleted and return.
        """
        return self._session_setattr( item, 'deleted', True, flush=flush )

    def undelete( self, trans, item, flush=True, **kwargs ):
        """
        Mark as not deleted and return.
        """
        return self._session_setattr( item, 'deleted', False, flush=flush )


class DeletableSerializerMixin( object ):

    def add_serializers( self ):
        self.serializable_keyset.add( 'deleted' )


# TODO: these are of questionable value if we don't want to enable users to delete/purge via update
class DeletableDeserializerMixin( object ):

    def add_deserializers( self ):
        self.deserializers[ 'deleted' ] = self.deserialize_deleted

    def deserialize_deleted( self, trans, item, key, val ):
        """
        Delete or undelete `item` based on `val` then return `item.deleted`.
        """
        new_deleted = self.validate.bool( key, val )
        if new_deleted == item.deleted:
            return item.deleted
        # TODO:?? flush=False?
        if new_deleted:
            self.manager.delete( trans, item, flush=False )
        else:
            self.manager.undelete( trans, item, flush=False )
        return item.deleted


class DeletableFiltersMixin( object ):

    def _add_parsers( self ):
        self.orm_filter_parsers.update({
            'deleted'       : { 'op': ( 'eq' ), 'val': self.parse_bool }
        })


class PurgableManagerMixin( DeletableManagerMixin ):
    """
    A manager interface/mixin for a resource that allows deleting and purging where
    purging is often removal of some additional, non-db resource (e.g. a dataset's
    file).
    """

    def purge( self, trans, item, flush=True, **kwargs ):
        """
        Mark as purged and return.

        Override this in subclasses to do the additional resource removal.
        """
        return self._session_setattr( item, 'purged', True, flush=flush )


class PurgableSerializerMixin( DeletableSerializerMixin ):

    def add_serializers( self ):
        DeletableSerializerMixin.add_serializers( self )
        self.serializable_keyset.add( 'purged' )


class PurgableDeserializerMixin( DeletableDeserializerMixin ):

    def add_deserializers( self ):
        DeletableDeserializerMixin.add_deserializers( self )
        self.deserializers[ 'purged' ] = self.deserialize_purged

    def deserialize_purged( self, trans, item, key, val ):
        """
        If `val` is True, purge `item` and return `item.purged`.
        """
        new_purged = self.validate.bool( key, val )
        if new_purged == item.purged:
            return item.purged
        if new_purged:
            self.manager.purge( trans, item, flush=False )
        return item.purged


class PurgableFiltersMixin( DeletableFiltersMixin ):

    def _add_parsers( self ):
        DeletableFiltersMixin._add_parsers( self )
        self.orm_filter_parsers.update({
            'purged'        : { 'op': ( 'eq' ), 'val': self.parse_bool }
        })
