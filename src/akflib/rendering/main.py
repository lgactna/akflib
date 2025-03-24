from collections import defaultdict
from pathlib import Path
from typing import Type

from caselib.uco.core import Bundle

from akflib.rendering.core import CASERenderer


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

    # Begin by grouping renderers as needed.
    grouped_outputs: dict[str, list[str]] = defaultdict(list)
    if group_renderers:
        for renderer_class, output in rendered_outputs.items():
            group_name = renderer_class.group
            grouped_outputs[group_name].append(output)
    else:
        grouped_outputs = {"default": list(rendered_outputs.values())}

    # For each group, combine them into a single document. Insert two newlines
    # between each document to separate them, and start the document with a level
    # 1 header containing the group name.
    documents = {}
    for group_name, group_outputs in grouped_outputs.items():
        document = f"# {group_name}\n\n"
        document += "\n\n".join(group_outputs)
        documents[group_name] = document

    return documents


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
    # TODO: can we just auto-detect where pandoc is

    # TODO: steal fastlabel's code

    # TODO: actually implement some renderers and test if this whole pipeline
    #       even works

    raise NotImplementedError


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
