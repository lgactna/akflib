"""
https://www.hecfblog.com/2016/04/daily-blog-367-automating-dfir-with.html
https://github.com/open-source-dfir/dfvfs-snippets/blob/main/scripts/source_analyzer.py
"""

import logging
import sys

from dfvfs.analyzer import analyzer
from dfvfs.credentials import manager as credentials_manager
from dfvfs.helpers import (
    command_line,
    file_system_searcher,
    source_scanner,
    volume_scanner,
)
from dfvfs.lib import definitions
from dfvfs.lib import definitions as dfvfs_definitions
from dfvfs.lib import errors as dfvfs_errors
from dfvfs.path import factory
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver
from dfvfs.volume import tsk_volume_system

# Only the following formats are supported:
# https://dfvfs.readthedocs.io/en/latest/sources/Supported-formats.html
#
# This, in fact, does not include VDI or AD1. Despite this, it'll still run
# and give you an OSPathSpec that just points to your own filesystem.

# source_path = "example.iso"
source_path = "C:\\Users\\Kisun\\Downloads\\decrypted.iso"
# source_path = "C:\\Users\\Kisun\\Downloads\\img.vmdk"

# internal_path = "akflib/actions/sample.py"
internal_path = "Users\\user\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\agent.exe"

# Note a few things - the path has to be correct for the underlying filesystem.
# For NTFS, it doesn't have a leading slash. Additionally, for NTFS, it cannot
# use POSIX separators. It must use Windows-style separators.

#####

# scanner = source_scanner.SourceScanner()
# scan_context = source_scanner.SourceScannerContext()

# scan_context.OpenSourcePath(source_path)

# scanner.Scan(
#     scan_context,
#     auto_recurse=True,
#     scan_path_spec=None
# )

# base_path_specs = scanner.GetBasePathSpecs(source_path)

#####

from dfvfs.vfs.file_entry import FileEntry
from dfvfs.vfs.file_system import FileSystem


def get_file_entry(file_system, path_spec):
    """Retrieves the file entry for a specific path specification."""
    try:
        file_entry = resolver.Resolver.OpenFileEntry(path_spec)
    except dfvfs_errors.BackEndError as exception:
        print(f"Unable to open file entry with error: {exception}")
        return None
    return file_entry


def calculate_slack_space(file_entry: FileEntry):
    """Calculates the slack space for a given file entry."""
    slack_space = 0
    for data_stream in file_entry.data_streams:
        for extent in data_stream.GetExtents():
            print(f"offset: {extent.offset}, size: {extent.size}")
            print(f"file size: {file_entry.size}")

            if extent.offset + extent.size > file_entry.size:
                slack_space += (extent.offset + extent.size) - file_entry.size
    return slack_space


# This will ask you for the partition... is there any way to automatically
# determine it, or otherwise specify it? One option is that we could subclass
# CLIVolumeScannerMediator and just bypass the prompt entirely, and select
# whichever the largest partition is. That's not foolproof.
#
# Anyways, it's not exactly the greatest option considering that you can't even
# directly edit virtual drives without a lot of effort (you'd have to unpack
# the drive and then mess with the compressed data).
mediator = command_line.CLIVolumeScannerMediator()

scanner = volume_scanner.VolumeScanner(mediator=mediator)
base_path_specs = scanner.GetBasePathSpecs(source_path)

# print(base_path_specs)


file_system: FileSystem = resolver.Resolver.OpenFileSystem(base_path_specs[0])
print(file_system)

spec = factory.Factory.NewPathSpec(
    # Get path spec indicator for the current file system
    file_system.GetRootFileEntry().path_spec.type_indicator,
    location=internal_path,
    parent=base_path_specs[0],
)


# print(file_system.GetRootFileEntry())
entry: FileEntry = file_system.GetFileEntryByPathSpec(spec)
if entry is None:
    print("File not found")
    exit()

print(calculate_slack_space(entry))

# file_system.GetFileEntryByPathSpec(base_path_specs[0])

# file_path_spec = path_spec_factory.Factory.NewPathSpec(
#     definitions.TYPE_INDICATOR_TSK, location="/", parent=base_path_specs[0]
# )

# file_entry = get_file_entry(file_system, file_path_spec)
# print(file_entry)
