from caselib import uco

from abc import ABC, abstractmethod

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
    
    @classmethod
    @abstractmethod
    def get_group(cls) -> str:
        """
        Return the group that this renderer belongs to.
        """
        pass
    