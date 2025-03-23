from abc import ABC, abstractmethod
from typing import ClassVar, Type

from caselib import uco

class CASERenderer(ABC):
    """
    Abstract base class for all CASE renderers.
    
    CASE renderers accept a complete CASE bundle, extract a specific set of
    objects, and generate a Markdown document from the result. 
    
    They also include some top-level metadata, such as the name of the section,
    the "group" that the renderer belongs to (so that sections of the same
    group can be separated into their own documents, if needed), and the specific
    UCO/CASE objects types that it handles.
    """
    
    # The human-readable name of this renderer.
    name: ClassVar[str]
    
    # The group that this renderer belongs to. May be any arbitrary string.
    #
    # This can be used to separate the outputs of different renderers into different
    # documents. When enabled, the outputs of all renderers from the same group 
    # will be placed into the same document.
    group: ClassVar[str]
    
    # The UCO/CASE object types that this renderer can handle.
    object_types: ClassVar[Type[uco.core.UcoObject]]
    
    def __init_subclass__(cls) -> None:
        """
        Check that subclasses have required attributes.
        """
        REQUIRED_ATTRIBUTES = ['name', 'group', 'object_types']
        for attr in REQUIRED_ATTRIBUTES:
            if not hasattr(cls, attr):
                raise TypeError(f"Can't instantiate abstract class {cls.__name__} "
                                f"without required attribute '{attr}'")
    