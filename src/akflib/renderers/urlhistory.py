"""
Render information from URLHistory objects.
"""

import logging
from pathlib import Path
from typing import Any, ClassVar, Type

from caselib.uco.core import UcoObject, UcoThing
from caselib.uco.observable import (
    URL,
    Application,
    ApplicationFacet,
    URLFacet,
    URLHistory,
    URLHistoryEntry,
    URLHistoryFacet,
)
from tabulate import tabulate

from akflib.rendering.objs import CASERenderer

logger = logging.getLogger(__name__)


class URLHistoryRenderer(CASERenderer):
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
        result = ""

        # Header
        result += "## Browser histories\n\n"

        # For each URLHistory object, which is assumed to be a single browser,
        # create a new level-3 section and list out the details
        for idx, obj in enumerate(objects, start=1):
            if not isinstance(obj, URLHistory):
                logger.warning(f"Object {obj} is not a URLHistory object, skipping")
                continue

            # Extract facets - we only expect a single facet
            facet = obj.hasFacet

            # If `facets` is a list, take the first element
            if isinstance(facet, list) and len(facet) > 0:
                facet = facet[0]

            if not isinstance(facet, URLHistoryFacet):
                logger.warning(
                    f"Facet {facet} is not a URLHistoryFacet object, skipping"
                )
                continue

            # If we have browserInformation and it's an Application object,
            # extract the applicationIdentifier
            app = facet.browserInformation
            app_id = f"Browser: unknown ({idx})"
            if isinstance(app, Application):
                app_facet = app.hasFacet
                if isinstance(app_facet, list) and len(app_facet) > 0:
                    app_facet = app_facet[0]
                if isinstance(app_facet, ApplicationFacet):
                    app_id = (
                        app_facet.applicationIdentifier
                        if app_facet.applicationIdentifier
                        else "?"
                    )

            result += f"### Browser: {app_id} ({idx})\n\n"

            if not facet.urlHistoryEntry:
                result += "No URL history entries found.\n\n"
                continue

            if not isinstance(facet.urlHistoryEntry, list):
                facet.urlHistoryEntry = [facet.urlHistoryEntry]

            # Now start extracting individual URLHistoryEntries, store in a table
            headers = ["URL", "Title", "Last accessed", "Visit count"]
            data: list[list[Any]] = []
            for history_entry in facet.urlHistoryEntry:
                if not isinstance(history_entry, URLHistoryEntry):
                    logger.warning(
                        f"Entry {history_entry} is not a URLHistoryEntry object, skipping"
                    )
                    continue

                # Extract the URL, title, last accessed date, and visit count
                url = history_entry.url
                if not isinstance(url, URL):
                    logger.warning(f"URL {url} is not a URL object, skipping")
                    continue

                if not url.hasFacet:
                    logger.warning(f"URL {url} has no facets, skipping")
                    continue

                # Flatten facet if it's a list, we should only have one URLFacet
                url_facet = url.hasFacet
                if isinstance(url_facet, list) and len(url_facet) > 0:
                    url_facet = url_facet[0]

                if not isinstance(url_facet, URLFacet):
                    logger.warning(
                        f"Facet {url_facet} is not a URLFacet object, skipping"
                    )
                    continue

                url_entry = url_facet.fullValue
                title = history_entry.pageTitle if history_entry.pageTitle else "?"
                last_accessed = (
                    history_entry.lastVisit.strftime("%Y-%m-%dT%H:%M:%S")
                    if history_entry.lastVisit
                    else "?"
                )
                visit_count = (
                    history_entry.visitCount if history_entry.visitCount else "?"
                )

                data.append([url_entry, title, last_accessed, visit_count])

            # Render using tabulate
            result += tabulate(data, headers=headers, tablefmt="github") + "\n\n"

        return result
