"""
The generic disk library for opening and interacting with filesystems, primarily
using dfvfs.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from dfvfs.helpers import command_line, volume_scanner
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver
from dfvfs.vfs.file_entry import FileEntry
from dfvfs.vfs.file_system import FileSystem
from dfvfs.volume.volume_system import Volume, VolumeExtent, VolumeSystem

logger = logging.getLogger(__name__)


@dataclass
class VolumeInfo:
    """
    A dataclass that stores various information about a volume in use.
    """

    volume_system: VolumeSystem
    selected_volume: Volume
    volume_extent: VolumeExtent

    volume_extent_offset: int
    volume_extent_size: int


# mypy can't see class information from dfvfs, so we have to ignore the error
class AutoSelectMediator(command_line.CLIVolumeScannerMediator):  # type: ignore[misc]
    """
    DFVFS volume scanner mediator that allows automatic selection of the largest
    volume, rather than prompting the user for the partition identifier on stdin.

    This mediator allows you to also manually select the partition, if desired.
    This is still an improvement over CLIVolumeScannerMediator, as it allows you
    to get details about the selected partition - information that is normally
    not available through the base CLIVolumeScannerMediator.

    (certainly, there are less obtuse ways to do this)
    """

    def __init__(self, auto_select: bool = True, volume_identifier: str | None = None):
        """
        Initializes the mediator.

        :param auto_select: Whether to automatically select the largest partition.
            If `False`, the user will be prompted to select a partition using
            the normal behavior of `CLIVolumeScannerMediator`.
        :param volume_identifier: The volume identifier to select. If provided,
            this will override the auto_select behavior and select the specified
            volume.
        """
        super().__init__()
        self.auto_select: bool = auto_select
        self.volume_identifier: str | None = volume_identifier

        self.volume_system: VolumeSystem | None = None
        self.selected_volume: Volume | None = None
        self.volume_extent: VolumeExtent | None = None

        self.volume_extent_offset: int | None = None
        self.volume_extent_size: int | None = None

    def GetPartitionIdentifiers(
        self, volume_system: VolumeSystem, volume_identifiers: list[str]
    ) -> list[str]:
        """
        Automatically selects the largest partition.

        This function is called by `dfvfs.helpers.volume_scanner.VolumeScanner` to
        determine which partition to use when multiple are available. It is never
        called if `len(volume_identifiers) <= 1`.
        """
        assert len(volume_identifiers) > 1

        # The default selection is the first partition
        volume_identifier = volume_identifiers[0]

        if self.volume_identifier:
            # If a volume identifier was provided, select it after asserting it exists
            if not volume_system.GetVolumeByIdentifier(self.volume_identifier):
                raise ValueError(
                    f"Volume identifier {self.volume_identifier} not found."
                )
            volume_identifier = self.volume_identifier
        elif not self.auto_select:
            logger.info(
                "Prompting user for partition, delegating to CLIVolumeScannerMediator"
            )

            # Run the normal behavior and extract the volume identifier manually
            result = super().GetPartitionIdentifiers(volume_system, volume_identifiers)
            assert len(result) == 1
            volume_identifier = result[0]
        else:
            logger.info("Automatically selecting largest partition")

            # Run through all available volume identifiers and select the largest one.
            largest_volume_size = 0

            for identifier in volume_identifiers:
                volume: Volume = volume_system.GetVolumeByIdentifier(identifier)

                if not volume:
                    # This should literally never happen
                    raise AssertionError(
                        f"Volume missing for identifier: {identifier}."
                    )

                volume_extent: VolumeExtent = volume.extents[0]
                assert isinstance(volume_extent, VolumeExtent)

                volume_size = volume_extent.size
                if volume_size > largest_volume_size:
                    largest_volume_size = volume_size
                    volume_identifier = identifier

        # Assign attributes now
        self.volume_system = volume_system
        self.selected_volume = self.volume_system.GetVolumeByIdentifier(
            volume_identifier
        )
        self.volume_extent = self.selected_volume.extents[0]
        self.volume_extent_offset = self.volume_extent.offset
        self.volume_extent_size = self.volume_extent.size

        logger.info(
            f"Volume selected: {volume_identifier} ({self.volume_extent.offset=}, {volume_extent.size=})"
        )

        # This function returns a list of identifiers, even though we're only
        # selecting one
        selected_volume_identifiers = [volume_identifier]
        return selected_volume_identifiers

    def to_volume_info(self) -> VolumeInfo:
        """
        Extract the volume information from this mediator.
        """

        # Check that all attributes are set
        if not all(
            [
                self.volume_system,
                self.selected_volume,
                self.volume_extent,
                self.volume_extent_offset,
                self.volume_extent_size,
            ]
        ):
            raise RuntimeError("One or more volume attributes have not been set")

        # although we check that all attributes are set, mypy doesn't know that
        return VolumeInfo(
            volume_system=self.volume_system,
            selected_volume=self.selected_volume,
            volume_extent=self.volume_extent,
            volume_extent_offset=self.volume_extent_offset,  # type: ignore[arg-type]
            volume_extent_size=self.volume_extent_size,  # type: ignore[arg-type]
        )


def open_file_system(
    image_path: Path, auto_select: bool = True, volume_identifier: str | None = None
) -> tuple[FileSystem, VolumeInfo]:
    """
    Opens a filesystem using the given image path.

    :param image_path: The path to the image file to open.
    :param auto_select: Whether to automatically select the largest partition.
        If `False`, the user will be prompted to select a partition using
        the normal behavior of `CLIVolumeScannerMediator`.
    :return: A tuple containing the opened filesystem and the volume information.
    """

    mediator = AutoSelectMediator(
        auto_select=auto_select, volume_identifier=volume_identifier
    )
    scanner = volume_scanner.VolumeScanner(mediator=mediator)

    base_path_specs = scanner.GetBasePathSpecs(str(image_path.resolve()))
    file_system: FileSystem = resolver.Resolver.OpenFileSystem(base_path_specs[0])

    return file_system, mediator.to_volume_info()


def get_file_entry(file_system: FileSystem, location: str) -> FileEntry | None:
    """
    Retrieves a file entry from the given filesystem.

    :param file_system: The filesystem to retrieve the file entry from.
    :param location: The location of the file entry to retrieve.
    :return: The file entry, or None if it could not be found.
    """

    try:
        spec = path_spec_factory.Factory.NewPathSpec(
            file_system.GetRootFileEntry().path_spec.type_indicator,
            location=location,
            parent=file_system._path_spec,
        )
    except ValueError as e:
        raise RuntimeError(
            "The provided path is unsupported for this filesystem."
            " Are you sure this is a supported, unencrypted disk or filesystem?"
        ) from e

    return file_system.GetFileEntryByPathSpec(spec)
