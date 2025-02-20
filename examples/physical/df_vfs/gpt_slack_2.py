import sys

from dfvfs.helpers import source_scanner, volume_scanner
from dfvfs.lib import definitions
from dfvfs.lib import errors as dfvfs_errors
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver


def get_file_entry(file_system, path_spec):
    """Retrieves the file entry for a specific path specification."""
    try:
        file_entry = resolver.Resolver.OpenFileEntry(path_spec)
    except dfvfs_errors.BackEndError as exception:
        print(f"Unable to open file entry with error: {exception}")
        return None
    return file_entry


def calculate_slack_space(file_entry):
    """Calculates the slack space for a given file entry."""
    slack_space = 0
    for data_stream in file_entry.data_streams:
        for extent in data_stream.extents:
            if extent.offset + extent.size > file_entry.size:
                slack_space += (extent.offset + extent.size) - file_entry.size
    return slack_space


def main(source_path, file_path):
    # Initialize the source scanner
    scanner = source_scanner.SourceScanner()

    # Create a source scanner context
    scan_context = source_scanner.SourceScannerContext()

    # Set the source path in the context
    scan_context.OpenSourcePath(source_path)

    # Scan the source path
    scanner.Scan(scan_context)

    # Get the volume scanner
    volume_scanner_object = volume_scanner.VolumeScanner(scanner)

    # Get the path specification of the file system
    path_spec = volume_scanner_object.GetBasePathSpec(scan_context)

    # Open the file system
    file_system = resolver.Resolver.OpenFileSystem(path_spec)

    # Get the path specification of the file
    file_path_spec = path_spec_factory.Factory.NewPathSpec(
        definitions.TYPE_INDICATOR_TSK, location=file_path, parent=path_spec
    )

    # Get the file entry
    file_entry = get_file_entry(file_system, file_path_spec)
    if not file_entry:
        print(f"File not found: {file_path}")
        return

    # Calculate the slack space
    slack_space = calculate_slack_space(file_entry)
    print(f"Slack space for file {file_path}: {slack_space} bytes")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <path_to_image> <file_path_in_image>")
        sys.exit(1)

    source_path = sys.argv[1]
    file_path = sys.argv[2]
    main(source_path, file_path)
