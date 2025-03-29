"""
Core routines/definitions for CASE rendering.
"""

import inspect
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from types import UnionType
from typing import Any, ClassVar, Iterable, Type, Union, get_args, get_origin

from caselib.uco.core import Bundle, UcoObject, UcoThing

logger = logging.getLogger(__name__)


def update_index_recursive(obj: UcoObject, akf_bundle: "AKFBundle") -> None:
    akf_bundle._add_obj_to_index(obj)

    # For object types that have fields accepting more UcoThings (list or
    # single instance), extract and process those as well
    #
    # Although akf_bundle.object only takes UcoObjects, our index accepts
    # UcoThings as well.
    list_fields = get_uco_thing_fields(type(obj))

    for field in list_fields:
        field_value = getattr(obj, field)
        if isinstance(field_value, list):
            for item in field_value:
                update_index_recursive(item, akf_bundle)
        elif issubclass(type(field_value), UcoThing):
            update_index_recursive(field_value, akf_bundle)


class AKFBundle(Bundle):
    """
    A specialized version of a UCO bundle that is optimized for AKF rendering.

    Instances of this class maintain a dictionary of UCO object types to
    lists of objects of that type. This allows for renderers to quickly
    locate objects of a particular type, rather than having to iterate through
    an entire bundle at render time.

    This class provides two convenience methods:
    - `add_object()`: Add a UCO object to the bundle and update the internal
      object dictionary.
    - `from_bundle()`: Create an AKFBundle from a regular UCO bundle. This allows
      you to pay the cost of object indexing up front.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._object_index: dict[Type[UcoThing], list[UcoThing]] = defaultdict(list)

    def _add_obj_to_index(self, obj: UcoObject) -> None:
        """
        Add a UCO object to the internal object index, non-recursively.
        """
        self._object_index[type(obj)].append(obj)

    def _add_obj_to_obj_list(self, obj: UcoObject) -> None:
        """
        Add an object to the `object` attribute, converting it to a list if
        necessary.
        """

        if not isinstance(self.object, list):
            # If the bundle is not a list, convert it to a list
            if self.object is None:
                self.object = []
            else:
                self.object = [self.object]

        assert isinstance(self.object, list)
        self.object.append(obj)

    def add_object(self, obj: UcoObject) -> None:
        """
        Add a UCO object to the bundle and update the internal object index.
        """
        self._add_obj_to_obj_list(obj)
        update_index_recursive(obj, self)

    def add_objects(self, objs: Iterable[UcoObject]) -> None:
        """
        Add a list of UCO objects to the bundle and update the internal object index.
        """
        for obj in objs:
            self._add_obj_to_obj_list(obj)
            update_index_recursive(obj, self)

    def write_to_jsonld(self, output_path: Path, indent: int = 2) -> None:
        """
        Write the AKFBundle to a JSON-LD file.
        """
        with open(output_path, "wt+") as f:
            data = self.model_dump(serialize_as_any=True)
            
            # Overwrite the @type and pretend we're actually a Bundle
            data['@type'] = "uco-core:Bundle"
            
            f.write(json.dumps(data, indent=indent))

    @classmethod
    def from_bundle(cls, bundle: Bundle) -> "AKFBundle":
        """
        Create an AKFBundle from a regular UCO bundle.
        """
        akf_bundle = cls()

        if isinstance(bundle.object, list):
            for obj in bundle.object:
                update_index_recursive(obj, akf_bundle)
        elif isinstance(bundle.object, UcoObject):
            update_index_recursive(bundle.object, akf_bundle)

        return akf_bundle


def get_uco_thing_fields(model_class: Type[UcoThing]) -> list[str]:
    """
    Extract all fields from a UcoThing subclass that allows for lists or single
    instances of UcoThing.

    :param model_class: A UcoThing subclass.
    :return: A list of field names that allow for lists of UcoThing.
    """
    result = []
    fields = model_class.model_fields

    for field_name, field_info in fields.items():
        annotation = field_info.annotation

        # Check if the annotation is directly list[UcoThing] or any subclass
        if _accepts_uco_thing(annotation):
            result.append(field_name)
            continue

        # Check if it's a Union/Optional that contains list[UcoObject] or list[UcoSubclass]
        #
        # Fun fact: Union (i.e. typing.Union) and using | (i.e. UnionType)
        # are different.
        if get_origin(annotation) is Union or get_origin(annotation) is UnionType:
            union_args = get_args(annotation)

            for arg in union_args:
                if _accepts_uco_thing(arg):
                    result.append(field_name)
                    break

    return result


def _accepts_uco_thing(annotation: Any) -> bool:
    """
    Check if an annotation is list[UcoThing] or a single instance of any UcoThing
    subclass.

    Some things, particularly facets, are not subclasses of UcoObject - they're
    subclasses of UcoThing. The majority of the code here checks for UcoObject
    since that's what's expected inside the `object` attribute of a bundle.

    However, we actually care about all objects here, so we check for the more
    general UcoThing type instead.
    """
    # Check for immediate subclasses of UcoThing (a single instance of it)
    if inspect.isclass(annotation) and issubclass(annotation, UcoThing):
        return True

    # Anything else has to be a list of UcoThings
    if get_origin(annotation) is not list:
        return False

    args = get_args(annotation)
    if len(args) != 1:
        return False

    # Check if list annotation is UcoThing or a subclass of UcoThing.
    arg_type = args[0]
    if isinstance(arg_type, type) and issubclass(arg_type, UcoThing):
        return True

    return False


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

    # The internal name for this renderer. It should be unique across all renderers.
    name: ClassVar[str]

    # The group that this renderer belongs to. May be any arbitrary string.
    #
    # This can be used to separate the outputs of different renderers into different
    # documents. When enabled, the outputs of all renderers from the same group
    # will be placed into the same document.
    group: ClassVar[str]

    # The UCO/CASE object types that this renderer can handle.
    object_types: ClassVar[list[Type[UcoObject]]]

    def __init_subclass__(cls) -> None:
        """
        Check that subclasses have required attributes.
        """
        REQUIRED_ATTRIBUTES = ["name", "group", "object_types"]
        for attr in REQUIRED_ATTRIBUTES:
            if not hasattr(cls, attr):
                raise TypeError(
                    f"Can't instantiate abstract class {cls.__name__} "
                    f"without required attribute '{attr}'"
                )

    @classmethod
    def _extract_related_objects(cls, bundle: Bundle) -> list[UcoThing]:
        """
        Recursively get all objects of the types declared in `object_types` from a
        UCO bundle.
        """
        objects = []

        # If the bundle is an AKFBundle, we can use the internal object index
        if isinstance(bundle, AKFBundle):
            for obj_type in cls.object_types:
                objects.extend(bundle._object_index.get(obj_type, []))
            return objects

        def _extract_objects_recursive(obj: UcoThing) -> list[UcoThing]:
            r_objects = []

            # Extract objects of the types declared in `object_types`
            for obj_type in cls.object_types:
                if issubclass(type(obj), obj_type) and not obj._is_reference:
                    logger.debug(f"Extracted object: {obj}")
                    r_objects.append(obj)

            # For object types that have fields accepting more UcoThing,
            # extract and process those as well
            list_fields = get_uco_thing_fields(type(obj))
            for field in list_fields:
                field_value = getattr(obj, field)
                if isinstance(field_value, list):
                    for item in field_value:
                        r_objects.extend(_extract_objects_recursive(item))
                elif issubclass(type(field_value), UcoThing):
                    r_objects.extend(_extract_objects_recursive(field_value))

            return r_objects

        if isinstance(bundle.object, list):
            for obj in bundle.object:
                objects.extend(_extract_objects_recursive(obj))
        elif isinstance(bundle.object, UcoThing):
            objects.extend(_extract_objects_recursive(bundle.object))

        return objects

    @classmethod
    @abstractmethod
    def render_objects(cls, objects: list[UcoThing], base_asset_folder: Path) -> str:
        """
        Process a list of UCO objects and return a Markdown document.

        The generated Markdown document should adhere to Pandoc-style Markdown.
        Implementations of this function may generate complex documents and
        place them in a folder relative to `base_asset_folder`, typically with
        the same name as the renderer itself. The absolute path of
        `base_asset_folder` will be provided to Pandoc as `--resource-path`;
        subclasses are responsible for generating correct relative or absolute
        paths to any assets that should be embedded in the document.

        For consistency, the renderer should generate a document with a level 2
        heading (##) as its top-level header.

        This function assumes that the objects supported by this renderer have
        already been extracted from a bundle. (Technically, this can be used to
        process any list of UCO/CASE objects, but it's intended to be used in
        conjunction with `_extract_objects()`.)
        """
        raise NotImplementedError

    @classmethod
    def render_bundle(cls, bundle: Bundle, base_asset_folder: Path) -> str:
        """
        Process a complete CASE bundle and return a Markdown document.

        The object types declared in `object_types` should be extracted from the
        bundle and processed by the renderer.
        """
        objects = cls._extract_related_objects(bundle)
        return cls.render_objects(objects, base_asset_folder)
