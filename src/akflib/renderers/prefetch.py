"""
Render information from (a sequence of) WindowsPrefetch objects.
"""

from pathlib import Path
from typing import ClassVar, Type

from akflib.rendering.objs import CASERenderer

from caselib.uco.observable import WindowsPrefetch
from caselib.uco.core import UcoObject, UcoThing

class PrefetchRenderer(CASERenderer):
    """
    Render WindowsPrefetch objects.
    """
    
    name: ClassVar[str] = "windows-prefetch"
    group: ClassVar[str] = "windows-artifacts"
    object_types: ClassVar[list[Type[UcoObject]]] = [WindowsPrefetch]
    
    @classmethod
    def render_objects(cls, objects: list[UcoThing], base_asset_folder: Path) -> str:
        """
        Render a sequence of WindowsPrefetch objects.
        
        :param objects: The list of WindowsPrefetch objects to render.
        :param base_asset_folder: The folder to place assets in. This is unused
            for PrefetchRenderer.
        :return: A string containing the rendered output.
        """
        result = ""
        
        # Header
        result += "## Windows Prefetch files\n\n"
    
        raise NotImplementedError