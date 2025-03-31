import logging
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Type

from caselib.uco.core import Bundle

from akflib.rendering.objs import CASERenderer
from akflib.utility.imports import get_objects_by_name

logger = logging.getLogger(__name__)


def render_bundle(
    bundle: Bundle, renderers: list[Type[CASERenderer]], base_asset_folder: Path
) -> dict[Type[CASERenderer], str]:
    """
    Pass a UCO/CASE bundle through a sequence of renderers.

    The renderers are applied in the order they are provided. The result is a
    dictionary that maps the renderer type to the rendered output.

    :param bundle: The UCO bundle to render.
    :param renderers: A list of renderer classes.
    :return: A dictionary that maps renderer classes to the rendered output.
    """

    results = {}
    for renderer_class in renderers:
        logger.info(f"Running renderer: {renderer_class.name} ({renderer_class})")
        results[renderer_class] = renderer_class.render_bundle(
            bundle, base_asset_folder
        )

    return results


def generate_documents(
    rendered_outputs: dict[Type[CASERenderer], str], group_renderers: bool = False
) -> dict[str, str]:
    """
    Generate complete Markdown documents from a dictionary of rendered outputs.

    The result is a dictionary of group names to complete Markdown documents.

    If group_renderers is True, the documents are grouped by renderer type.
    Otherwise, this returns a single document that concatenates all outputs
    as the dictionary key "default".
    """

    logger.info(f"Compiling documents from {len(rendered_outputs)} renderers")

    # Begin by grouping renderers as needed.
    grouped_outputs: dict[str, list[str]] = defaultdict(list)
    if group_renderers:
        for renderer_class, output in rendered_outputs.items():
            group_name = renderer_class.group
            grouped_outputs[group_name].append(output)
            logger.info(f"Grouped documents for {group_name=}")
    else:
        logger.info("Grouping disabled, using single group")
        grouped_outputs = {"Results": list(rendered_outputs.values())}

    logger.info(f"Produced {len(grouped_outputs)} document(s)")

    # For each group, combine them into a single document. Insert two newlines
    # between each document to separate them, and start the document with a level
    # 1 header containing the group name.
    documents = {}
    for group_name, group_outputs in grouped_outputs.items():
        document = f"# {group_name}\n\n"
        document += "\n\n".join(group_outputs)
        documents[group_name] = document

    return documents


def check_if_eisvogel_installed(pandoc_path: Path) -> bool:
    """
    Check if the Eisvogel template is installed for Pandoc.

    :param pandoc_path: The path to the Pandoc executable.
    :return: True if the Eisvogel template is installed, False otherwise.
    """
    try:
        # Get the user data directory
        result = subprocess.run(
            [pandoc_path, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        match = re.search(r"^User data directory:\s*(.*)$", result.stdout, re.MULTILINE)
        assert match

        return (Path(match.group(1)) / "templates/eisvogel.latex").exists()

    except subprocess.CalledProcessError:
        return False


def generate_pdfs(
    rendered_documents: dict[str, str],
    output_folder: Path,
    base_asset_folder: Path,
    pandoc_path: Path,
) -> None:
    """
    Generate PDFs with Pandoc using the provided document groups.

    The name of each PDF is simply the key of the dictionary (which should be
    the group name).

    :param rendered_documents: A dictionary of group names to complete Markdown documents.
    :param output_folder: The folder where the PDF(s) and any generated assets will
        be saved.
    :param base_asset_folder: The folder where the assets are stored.
    :param pandoc_path: The path to the Pandoc executable.
    """
    logger.info(f"Invoking Pandoc (at {pandoc_path})")

    # For each group in rendered_documents, generate a PDF using Pandoc.
    for group_name, document in rendered_documents.items():
        # Generate the output file name
        output_file = output_folder / f"{group_name}.pdf"

        # Write the document to a temporary file and add it to the command
        temp_file = output_file.with_suffix(".md")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(document)

        # Generate the command to run Pandoc
        command = [
            pandoc_path.as_posix(),
            temp_file.as_posix(),
            "-o",
            output_file.as_posix(),
            "-f",
            "markdown",
            "-t",
            "pdf",
            "--standalone",
            "--resource-path",
            base_asset_folder.as_posix(),
        ]

        # Check if the Eisvogel template is installed
        if check_if_eisvogel_installed(pandoc_path):
            logger.info("Eisvogel template is installed, using it")
            command.append("--template=eisvogel")
        else:
            logger.info("Eisvogel template is not installed")

        # Run the command
        logger.info(f"Running command: {' '.join(command)}")
        s = subprocess.run(command, check=True, capture_output=True)
        logger.info(f"Pandoc stdout: {s.stdout.decode('utf-8')}")
        logger.info(f"Pandoc stderr: {s.stderr.decode('utf-8')}")


def bundle_to_pdf(
    bundle: Bundle,
    renderers: list[Type[CASERenderer]],
    output_folder: Path,
    pandoc_path: Path,
    group_renderers: bool = False,
) -> None:
    """
    Analyze the contents of a UCO/CASE bundle to one or more PDF documents.

    When group_renderers is True, the outputs of the renderers are grouped by
    the group name of the renderer. This causes multiple documents to be generated,
    where each document's name is that of the group. Otherwise, a single document
    whose name is "default.pdf` is generated.

    :param bundle: The UCO/CASE bundle to render.
    :param renderers: A list of renderer classes to run on the bundle.
    :param output_folder: The folder where the PDF(s) and any generated assets will
        be saved.
    :param group_renderers: If True, group the outputs of the renderers into separate
        documents based on the group name of a renderer.
    """

    base_asset_folder = output_folder / "assets"

    outputs = render_bundle(bundle, renderers, base_asset_folder)
    documents = generate_documents(outputs, group_renderers)

    generate_pdfs(documents, output_folder, base_asset_folder, pandoc_path)


def get_renderer_classes(renderer_paths: Iterable[str]) -> list[Type[CASERenderer]]:
    """
    Given a list of fully-qualified import paths, render their corresponding
    CASERenderer classes.
    """
    result = get_objects_by_name(renderer_paths)

    for obj in result.values():
        if not issubclass(obj, CASERenderer):
            raise TypeError(f"{obj} is not a subclass of CASERenderer")

    return list(result.values())


def get_pandoc_path() -> Path | None:
    """
    Make a best-effort attempt to find the Pandoc executable.

    Paths are derived from this SO answer:
    https://stackoverflow.com/questions/28032436/where-is-pandoc-installed-on-windows
    """

    # If Pandoc is on PATH, just use that
    pandoc_from_path = shutil.which("pandoc")
    if pandoc_from_path:
        return Path(pandoc_from_path)

    # Check if Pandoc was probably installed for all users (either Program
    # Files or Program Files (x86))
    path = Path("C:/Program Files/Pandoc/pandoc.exe")
    if path.is_file():
        return path

    path = Path("C:/Program Files (x86)/Pandoc/pandoc.exe")
    if path.is_file():
        return path

    # Check if Pandoc was just installed for the current user
    local_appdata_path = os.getenv("LOCALAPPDATA")
    if not local_appdata_path:
        logger.warning("LOCALAPPDATA environment variable is not set")
        # Give up
        return None

    path = Path(local_appdata_path) / "Pandoc/pandoc.exe"
    if path.is_file():
        return path

    # we tried
    return None
