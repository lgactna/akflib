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
# source_path = "C:\\Users\\Kisun\\Downloads\\decrypted.vhd"
source_path = "C:\\Users\\Kisun\\Downloads\\decrypted-2.iso"
# source_path = "C:\\Users\\Kisun\\Downloads\\img.vmdk"

# internal_path = "akflib/actions/sample.py"
# internal_path = "Users\\user\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\agent2.exe"
# internal_path = "Users\\user\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\desktop.ini"

# To get the MFT entry of a file:
# - Get the absolute offset of the $MFT file, which is at the root of the filesystem
# - Get the MFT entry number of the file (using pytsk3 or similar)
# - Multiply the MFT entry number by the size of an MFT entry (usually 1024 bytes)
# - Add this to the absolute offset of the $MFT file
# - This is the offset of the MFT entry
#
# To get the size of an MFT entry:
# - Go to the very first sector of the volume
# - Read the byte at offset 0x40 
# - Interpret it as a signed integer (see https://en.wikipedia.org/wiki/NTFS#Partition_Boot_Sector_(PBS))
# - If:
#   - the value is positive, the size of an MFT entry is value*cluster_size
#   - the value is negative, the size of an MFT entry is 2^abs(value)
#        - in which case the bytes per sector is at offset 0x0B of the boot sector,
#          and the sectors per cluster is at offset 0x0D of the boot sector 
internal_path = "$MFT"


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


def calculate_slack_space(file_entry: FileEntry, block_size: int, absolute_offset: int = 0):
    """
    Calculates the slack space for a given file entry.
    
    There are three special cases:
    - The file is sparse, and has a nonzero declared size but a significantly
      larger actual size (and therefore has "negative" slack space).
    - The file is fragmented, and the slack space is distributed across multiple
      clusters. (currently can't be detected)
    - The file is resident, and has no slack space because it doesn't have any 
      clusters. The declared size is zero. Editing resident files is not supported
      since I don't know how to get the location of the MFT entry. 
      https://github.com/libyal/libfsntfs/blob/main/pyfsntfs/pyfsntfs_file_entry.c
      doesn't seem to expose anything.
    """
    # slack_space = 0
    
    actual_size = file_entry.size
    decl_size = 0
    
    last_cluster_size = 0
    
    for data_stream in file_entry.data_streams:
        for extent in data_stream.GetExtents():
            print(f"offset: {extent.offset} (absolute: {extent.offset + absolute_offset} - {extent.offset+absolute_offset+extent.size}), size: {extent.size}, {extent.size%block_size}")
            decl_size += extent.size

            last_cluster_size = extent.size
            # if extent.offset + extent.size > file_entry.size:
            #     slack_space += (extent.offset + extent.size) - file_entry.size
            
    # note that we assume slack space only exists in the final cluster. this is not necessarily guaranteed,
    # and i'm not sure what a more rigorous approach would entail given the informatoin exposed by dfvfs (since
    # we aren't able to get the filesystem block size)
    slack_space = decl_size - actual_size
    print(f"Declared size: {decl_size}, actual size: {actual_size}")
    print(f"Occupied size of final cluster: {last_cluster_size - slack_space} ({slack_space} bytes slack)")
    return slack_space


# This will ask you for the partition... is there any way to automatically
# determine it, or otherwise specify it? One option is that we could subclass
# CLIVolumeScannerMediator and just bypass the prompt entirely, and select
# whichever the largest partition is. That's not foolproof.
#
# Anyways, it's not exactly the greatest option considering that you can't even
# directly edit virtual drives without a lot of effort (you'd have to unpack
# the drive and then mess with the compressed data).
# Custom mediator that tracks the selected volume identifier
class AutoSelectMediator(command_line.CLIVolumeScannerMediator):
    def __init__(self):
        super().__init__()
        self.selected_volume_identifiers: list[str] | None = None
        self.volume_system = None
        
        self.volume_offset: int | None = None
        self.volume_size: int | None = None
    
    # def GetPartitionIdentifiers(self, volume_system, volume_identifiers):
    #     """Asks the user to provide the partition identifier."""
    #     self.volume_system = volume_system
    #     self.selected_volume_identifier = super().GetPartitionIdentifiers(volume_system, volume_identifiers)
    #     return self.selected_volume_identifier
    
    def GetPartitionIdentifiers(self, volume_system, volume_identifiers) -> list[str]:
        """Automatically selects the largest partition."""
        self.volume_system = volume_system

        largest_volume_size = 0
        largest_volume_identifier = volume_identifiers[0]        
        for identifier in volume_identifiers:
            volume = self.volume_system.GetVolumeByIdentifier(identifier)
            if not volume:
                raise RuntimeError(f'Volume missing for identifier: {identifier}.')
            
            volume_extent = volume.extents[0]
            volume_size = volume_extent.size
            if volume_size > largest_volume_size:
                largest_volume_size = volume_size
                largest_volume_identifier = identifier
        
        selected_volume = self.volume_system.GetVolumeByIdentifier(largest_volume_identifier)
        volume_extent = selected_volume.extents[0]
        print(f"Selected volume identifier: {largest_volume_identifier} ({volume_extent.offset=}, {volume_extent.size=})")
        
        self.selected_volume_identifiers = [largest_volume_identifier]
        
        return self.selected_volume_identifiers
    
    def GetVolumeInfo(self):
        """Prints information about the selected volume."""
        if not self.selected_volume_identifiers or not self.volume_system:
            return
            
        volume = self.volume_system.GetVolumeByIdentifier(self.selected_volume_identifiers[0])
        volume_extent = volume.extents[0]
        volume_offset = f'{volume_extent.offset:d} (0x{volume_extent.offset:08x})'
        volume_size = self._FormatHumanReadableSize(volume_extent.size)
        
        self.volume_offset = volume_extent.offset
        self.volume_size = volume_extent.size
        
        print(volume_offset, volume_size)

# Autoselect-largest or CLI volume scanner mediator
mediator = AutoSelectMediator()
# mediator = command_line.CLIVolumeScannerMediator()

scanner = volume_scanner.VolumeScanner(mediator=mediator)
base_path_specs = scanner.GetBasePathSpecs(source_path)

# Print volume information after selection
mediator.GetVolumeInfo()

# print(base_path_specs)


file_system: FileSystem = resolver.Resolver.OpenFileSystem(base_path_specs[0])
print(file_system)

try:
    spec = factory.Factory.NewPathSpec(
        # Get path spec indicator for the current file system
        file_system.GetRootFileEntry().path_spec.type_indicator,
        location=internal_path,
        parent=base_path_specs[0],
    )
except ValueError as e:
    print("Path spec is unsupported for this filesystem. Are you sure this is a supported, unencrypted disk or filesystem?")
    exit()


# print(file_system.GetRootFileEntry())
entry: FileEntry = file_system.GetFileEntryByPathSpec(spec)
if entry is None:
    print("File not found")
    exit()

print(calculate_slack_space(entry, 4096, mediator.volume_offset))

## Part 2: find the offset of the MFT entry of a file

import pytsk3

img = pytsk3.Img_Info(source_path)
# Enumerate partitions with Volume_Info
try:
    vol = pytsk3.Volume_Info(img)
except IOError:
    # If Volume_Info fails, the image may not have partitions, so just try FS_Info directly:
    print("No valid partition table found; attempting to parse file system at offset 0.")
    fs = pytsk3.FS_Info(img)
else:
    print("Partitions detected. Select which partition to analyze:\n")
    partitions = []
    for i, part in enumerate(vol):
        desc = part.desc.decode(errors="replace").strip()
        print(f"Partition {i}: Start={part.start}, Length={part.len}, Description={desc}")
        partitions.append(part)

    if not partitions:
        print("No partitions found; attempting to parse at offset 0.")
        fs = pytsk3.FS_Info(img)
    else:
        choice = input("\nEnter the partition number to use (default 0): ") or "0"
        choice_index = int(choice)
        if choice_index < 0 or choice_index >= len(partitions):
            print(f"Invalid selection. Using partition 0.")
            choice_index = 0

        selected_part = partitions[choice_index]
        offset_bytes = selected_part.start * 512  # typical sector size, adjust if known otherwise

        fs = pytsk3.FS_Info(img, offset=offset_bytes)
file_obj = fs.open(path="Users/user/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/desktop.ini")
print(file_obj.info.meta.addr)


# entry = file_system.GetFileEntryByPathSpec(base_path_specs[0])

# tsk_path_spec = path_spec_factory.Factory.NewPathSpec(
#     definitions.TYPE_INDICATOR_TSK, location="/", parent=base_path_specs[0]
# )
# resolver.Resolver.OpenFileEntry(tsk_path_spec)

# file_entry = get_file_entry(file_system, file_path_spec)
# print(file_entry)


