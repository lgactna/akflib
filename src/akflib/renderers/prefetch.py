"""
Render information from (a sequence of) WindowsPrefetch objects.
"""

from pathlib import Path
from typing import ClassVar, Type

from caselib.uco.core import UcoObject, UcoThing
from caselib.uco.observable import WindowsPrefetch, WindowsPrefetchFacet
from tabulate import tabulate

from akflib.rendering.objs import CASERenderer


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

        headers = ["Application", "Times executed", "Last run"]
        data = []

        # Go through each WindowsPrefetch object
        for obj in objects:
            if not isinstance(obj, WindowsPrefetch):
                continue

            # Extract facets - we only expect a single facet
            facet = obj.hasFacet

            # If `facets` is a list, take the first element
            if isinstance(facet, list) and len(facet) > 0:
                facet = facet[0]

            if not isinstance(facet, WindowsPrefetchFacet):
                continue

            data.append(
                [
                    facet.applicationFileName if facet.applicationFileName else "?",
                    facet.timesExecuted if facet.timesExecuted else "?",
                    (
                        facet.lastRun.strftime("%Y-%m-%dT%H:%M:%S")
                        if facet.lastRun
                        else "?"
                    ),
                ]
            )

        # Render with tabulate
        result += tabulate(data, headers=headers, tablefmt="github") + "\n\n"

        raise NotImplementedError
