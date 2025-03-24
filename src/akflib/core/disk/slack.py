"""
Various utilities for interacting with slack space on various file systems.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from dfvfs.vfs.data_stream import DataStream
from dfvfs.vfs.file_entry import FileEntry

logger = logging.getLogger(__name__)


@dataclass
class SlackSpaceMeta:
    """
    A dataclass that stores various information relevant to slack space calculations.

    This is the object type returned by `analyze_file_slack`.
    """

    # The actual size of the file, as reported by the filesystem.
    actual_size: int
    # The total size of the file's extents, which may not be the same as the
    # actual size.
    allocated_size: int
    # The slack space of the file, assumed to be the difference between the
    # allocated size and the actual size.
    slack_space: int

    # The `absolute_offset` parameter possed to `analyze_file_slack`, used to
    # calculate `last_cluster_offset_absolute`. Because `FileEntry` objects
    # are unaware of the filesystem's offset on a multi-partition disk, this is
    # required to correctly calculate the absolute offset of the last cluster
    # on a raw disk image.
    absolute_offset: int

    # The relative offset of the (beginning of) the last cluster/extent of the file
    # on the filesystem.
    final_extent_offset_relative: int
    # The absolute offset of the (beginning of) the last cluster/extent of the file,
    # which is the sum of `absolute_offset` and `last_cluster_offset_relative`.
    final_extent_offset_absolute: int
    # The allocated size of the last cluster. You can use this information to determine
    # the actual offset of the slack space; simply take `last_cluster_offset_absolute`
    # and add `last_cluster_size`, then subtract `slack_space`.
    final_extent_size: int
    # The offset of the beginning of slack space.
    slack_space_offset_absolute: int = 0

    # If the allocated size is less than the actual size, the file is assumed
    # to be sparse. In this case, it is generally unsafe to perform slack space
    # operations, as the calculated slack space and offsets may be incorrect.
    is_sparse: bool = False
    # If the allocated size is zero, the file is assumed to be resident. Performing
    # slack space operations on resident files requires additional information
    is_resident: bool = False


def analyze_file_slack(
    file_entry: FileEntry, absolute_offset: int = 0
) -> SlackSpaceMeta:
    """
    Naively calculates the slackspace for a given file entry, assuming that
    all slack space exists at the end of the final cluster/extent of a file.

    This function will return an instance of `SlackSpaceMeta` that contains
    information about the slack space of the file, including the location and
    size of the slack space (if any). Note that although the calculated slack
    space should be correct regardless of the underlying disk format, the
    offset returned in `last_cluster_offset_absolute` will only be correct
    for raw disk images.

    There are three special cases:
    - The file is sparse. In this case, the occupied size of the file is nonzero,
      but significantly less than the "actual" size of the file. In this case,
      this function returns a negative slack space.
    - The file is fragmented. In this case, slack space may be distributed in
      extents other than the last. I do not believe this can be trivially detected.
    - The file is resident, and has no slack space because it does not have
      any clusters.

    Cases 1 and 3 are denoted by `is_safe` and `is_resident` in the returned
    `SlackSpaceMeta` object. Case 2 cannot be detected by this function.

    :param file_entry: The DFVFS file entry to analyze.
    :param absolute_offset: The absolute offset of the filesystem on a raw disk image.
        This parameter is used to calculate the absolute offset of the last cluster,
        since knowledge of the filesystem's offset is required to calculate this;
        it is not stored in the `FileEntry` object. You most likely want this from
        `VolumeInfo.volume_extent_offset`.
    :return: A `SlackSpaceMeta` object containing information about the slack space.

    """
    # Get the "actual" size of the file, as reported by the filesystem
    actual_size = file_entry.size

    # Tally up the total space occupied by this file on disk, which is the sum of
    # the size of the file's extents. The file may not occupy the full size of
    # an extent.
    allocated_size = 0

    # Keep track of the size of the final cluster/extent.
    final_extent_size = 0
    final_extent_offset = 0

    for data_stream in file_entry.data_streams:
        assert isinstance(data_stream, DataStream)
        for extent in data_stream.GetExtents():
            allocated_size += extent.size
            final_extent_size = extent.size
            final_extent_offset = extent.offset

    # The slack space is assumed to be the difference between the total occupied
    # size and the actual size of the file.
    slack_space = allocated_size - actual_size

    # The actual beginning of slack space for this file can be calculated by
    # taking the size of the final extent, subtracting the slack space, and
    # adding the absolute offset of the final extent.
    relative_slack_space_offset = final_extent_offset + final_extent_size - slack_space
    absolute_slack_space_offset = absolute_offset + relative_slack_space_offset

    # If the allocated size is less than the actual size, the file is sparse.
    is_sparse = allocated_size < actual_size

    # If the allocated size is zero, the file is resident.
    is_resident = allocated_size == 0

    logger.debug(
        f"File size: {actual_size}, allocated size: {allocated_size}, slack space: {slack_space}."
    )
    logger.debug(
        f"Relative offset of final extent: {final_extent_offset}, size: {final_extent_size}."
    )
    logger.debug(
        f"Absolute offset of final extent: {absolute_offset + final_extent_offset}."
    )

    return SlackSpaceMeta(
        actual_size=actual_size,
        allocated_size=allocated_size,
        slack_space=slack_space,
        absolute_offset=absolute_offset,
        final_extent_size=final_extent_size,
        final_extent_offset_relative=final_extent_offset,
        final_extent_offset_absolute=absolute_offset + final_extent_offset,
        slack_space_offset_absolute=absolute_slack_space_offset,
        is_sparse=is_sparse,
        is_resident=is_resident,
    )


def insert_into_file_slack(image_path: Path, data: bytes, meta: SlackSpaceMeta) -> None:
    """
    Write data into the slack space of a file contained on a disk image.

    This function is intended to be called immediately after `analyze_file_slack`
    with the original disk image that was used to open the underlying filesystem.
    """

    # Check that the file is not sparse or resident
    if meta.is_sparse or meta.is_resident:
        raise ValueError("Cannot insert data into a sparse or resident file.")

    # Check that `image_path` exists
    if not image_path.exists():
        raise FileNotFoundError(f"Disk image {image_path} does not exist.")

    # Check that the underlying disk image is larger than what is indicated by
    # `meta.slack_space_offset_absolute`.
    if image_path.stat().st_size < meta.slack_space_offset_absolute:
        raise ValueError(
            "Disk image is smaller than the calculated slack space offset."
        )

    # Check that the data to write is smaller than the slack space
    if len(data) > meta.slack_space:
        raise ValueError("Data to write is larger than the calculated slack space.")

    logger.info(
        f"Writing {len(data)} bytes to slack space at offset {meta.slack_space_offset_absolute}."
    )

    # Open the disk image
    with open(image_path, "r+b") as f:
        # Seek to the calculated slack space offset
        f.seek(meta.slack_space_offset_absolute)
        # Write the data
        f.write(data)
