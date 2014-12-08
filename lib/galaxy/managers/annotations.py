import galaxy.model
import galaxy.util


class AnnotationManager( object ):
    """ Provides a unified interface for dealing with annotations across
    Galaxy models.
    """

    def __ini__( self ):
        pass

    def get_annotation_assoc_class( self, item ):
        """ Returns an item's item-annotation association class. """
        class_name = '%sAnnotationAssociation' % item.__class__.__name__
        return getattr( galaxy.model, class_name, None )

    def get_item_annotation_obj( self, db_session, user, item ):
        """ Returns a user's annotation object for an item. """
        # Get annotation association class.
        annotation_assoc_class = self.get_annotation_assoc_class( item )
        if not annotation_assoc_class:
            return None

        # Get annotation association object.
        annotation_assoc = db_session.query( annotation_assoc_class ).filter_by( user=user )

        # TODO: use filtering like that in _get_item_id_filter_str()
        if item.__class__ == galaxy.model.History:
            annotation_assoc = annotation_assoc.filter_by( history=item )
        elif item.__class__ == galaxy.model.HistoryDatasetAssociation:
            annotation_assoc = annotation_assoc.filter_by( hda=item )
        elif item.__class__ == galaxy.model.StoredWorkflow:
            annotation_assoc = annotation_assoc.filter_by( stored_workflow=item )
        elif item.__class__ == galaxy.model.WorkflowStep:
            annotation_assoc = annotation_assoc.filter_by( workflow_step=item )
        elif item.__class__ == galaxy.model.Page:
            annotation_assoc = annotation_assoc.filter_by( page=item )
        elif item.__class__ == galaxy.model.Visualization:
            annotation_assoc = annotation_assoc.filter_by( visualization=item )
        return annotation_assoc.first()

    def add_item_annotation( self, db_session, user, item, annotation ):
        """ Add or update an item's annotation; a user can only have a single annotation for an item. """
        # Get/create annotation association object.
        annotation_assoc = self.get_item_annotation_obj( db_session, user, item )
        if not annotation_assoc:
            annotation_assoc_class = self.get_annotation_assoc_class( item )
            if not annotation_assoc_class:
                return None
            annotation_assoc = annotation_assoc_class()
            item.annotations.append( annotation_assoc )
            annotation_assoc.user = user

        # Set annotation.
        annotation_assoc.annotation = annotation
        return annotation_assoc

    def get_item_annotation_str( self, db_session, user, item ):
        """ Returns a user's annotation string for an item. """
        annotation_obj = self.get_item_annotation_obj( db_session, user, item )
        if annotation_obj:
            return galaxy.util.unicodify( annotation_obj.annotation )
        return None

    def delete_item_annotation( self, db_session, user, item):
        annotation_assoc = self.get_item_annotation_obj( db_session, user, item )
        if annotation_assoc:
            db_session.delete(annotation_assoc)
            db_session.flush()

    def copy_item_annotation( self, db_session, source_user, source_item, target_user, target_item ):
        """ Copy an annotation from a user/item source to a user/item target. """
        if source_user and target_user:
            annotation_str = self.get_item_annotation_str( db_session, source_user, source_item )
            if annotation_str:
                annotation = self.add_item_annotation( db_session, target_user, target_item, annotation_str )
                return annotation
        return None
