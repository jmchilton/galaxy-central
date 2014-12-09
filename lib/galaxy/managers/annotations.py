from galaxy.model.item_attrs import UsesAnnotations


# Generally we are not 'mixin'-ing Managers - but it is particularily
# difficult to unwind UsesAnnotations because it is mixed into both
# controllers and models - so we cannot move its functionality into this
# package. Goal should be to replace all controller uses of that
# functionality with references to this AnnotationManager. Then we won't
# have cleaner dependency tiers (it would be controller -> managers
# -> models -> UsesAnnotations,UsesItemRatings).
class AnnotationManager( UsesAnnotations ):
    """ Provides a unified interface for dealing with annotations across
    Galaxy models.
    """
