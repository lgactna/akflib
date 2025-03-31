"""
Render information from URLHistory objects.
"""

from pathlib import Path
from typing import ClassVar, Type

from akflib.rendering.objs import CASERenderer

from caselib.uco.observable import URLHistory
from caselib.uco.core import UcoObject, UcoThing

class PrefetchRenderer(CASERenderer):
    """
    Render WindowsPrefetch objects.
    """
    
    name: ClassVar[str] = "urlhistory"
    group: ClassVar[str] = "browser-artifacts"
    object_types: ClassVar[list[Type[UcoObject]]] = [URLHistory]
    
    @classmethod
    def render_objects(cls, objects: list[UcoThing], base_asset_folder: Path) -> str:
        """
        Render a sequence of WindowsPrefetch objects.
        
        :param objects: The list of WindowsPrefetch objects to render.
        :param base_asset_folder: The folder to place assets in. This is unused
            for PrefetchRenderer.
        :return: A string containing the rendered output.
        """
        
        # Header
        result += "## Browser histories\n\n"
        
        # For each URLHistory object, which is assumed to be a single browser, 
        
        raise NotImplementedError
                
        # Generate body by iterating through objects
        
        
        # Generate the body of the document
        body = "\n\n".join([cls.render_prefetch(prefetch, base_asset_folder) for prefetch in objects])
        
        return header + body