"""
- Is it possible to use the `pytsk` library to analyze an existing filesystem
  (such as an ISO, raw disk image, or virtual hard drive) and determine the
  slack space a file at a known path on the filesystem, and if so, how?
  Furthermore, can the location of this slack space be determined so that a
  direct edit of the relevant bytes can be performed?
  
- Suppose that I am only interested in identifying the physical offset of a
  file's clusters, as well as determining if a file has any slack space.
  How might I achieve that using the pytsk library? Please provide a Python
  script in as much detail as possible.
  
- Can you modify this script to indicate the expected physical offset of the 
  beginning of slack space for the file as part of `print_file_runs()`?

"""

import sys
from pathlib import Path

import pytsk3


def print_file_runs(fs, file_obj):
    """
    Prints out physical runs for all data attributes in the file.
    Checks slack by comparing allocated size vs. the file's actual size,
    and indicates the physical offset at which slack begins (if any).
    """
    fs_block_size = fs.info.block_size
    runs_info = []

    # Gather info about each data attribute's runs
    for attr in file_obj:
        # Data attributes are typically TSK_FS_ATTR_TYPE_DEFAULT or
        # TSK_FS_ATTR_TYPE_NTFS_DATA (128) on NTFS.
        if (
            attr.info.type == pytsk3.TSK_FS_ATTR_TYPE_DEFAULT
            or attr.info.type == pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA
        ):
            for run in attr:
                if run.len > 0:  # 0 signals end of runs
                    physical_offset_bytes = run.addr * fs_block_size
                    physical_length_bytes = run.len * fs_block_size
                    runs_info.append(
                        {
                            "run_offset_in_file": run.offset,
                            "physical_offset": physical_offset_bytes,
                            "physical_len": physical_length_bytes,
                        }
                    )

    # Print each run’s info
    for i, info in enumerate(runs_info, start=1):
        print(f"Run #{i}:")
        print(
            f"  File offset range: [{info['run_offset_in_file']}, "
            f"{info['run_offset_in_file'] + info['physical_len']})"
        )
        print(f"  Physical offset: {info['physical_offset']}")
        print(f"  Physical length: {info['physical_len']}")

    meta = file_obj.info.meta
    if not meta:
        print("\nNo meta information for this file.")
        return

    # Compare actual file size to allocated size
    actual_size = meta.size

    # "Some filesystems do not expose a separate field for allocated size..."
    # https://sleuthkit.org/sleuthkit/docs/api-docs/4.10.0/structTSK__FS__META.html
    # does not indicate that allocsize exists (including for any filesystem-specific
    # unions.)
    #
    # allocated_size = meta.allocsize if meta.allocsize > 0 else sum(r['physical_len'] for r in runs_info)

    allocated_size = sum(r["physical_len"] for r in runs_info)
    print(f"\nActual size: {actual_size} bytes")
    print(f"Allocated size: {allocated_size} bytes")

    if allocated_size <= actual_size:
        print("No slack space.")
        return

    # File has slack space. Figure out where it starts.
    slack_size = allocated_size - actual_size
    print(f"Slack space: {slack_size} bytes")

    # Locate which run contains the last used byte of the file
    file_end = actual_size  # first byte after the file's data is actual_size
    for info in reversed(runs_info):
        start_of_run = info["run_offset_in_file"]
        end_of_run = start_of_run + info["physical_len"]
        if file_end > start_of_run:
            # The file's last data byte is in this run (or beyond if multiple runs).
            used_in_this_run = min(file_end, end_of_run) - start_of_run
            slack_begins_within_run = info["physical_offset"] + used_in_this_run
            print(f"Slack begins at physical offset: {slack_begins_within_run}")
            break


def find_file_in_fs(fs, path_to_file):
    """
    Opens the specified file path in the filesystem and returns a pytsk3.File object.
    """
    try:
        tsk_file = fs.open(path=path_to_file)
        return tsk_file
    except IOError:
        print(f"Could not find or open file: {path_to_file}")
        sys.exit(1)


def main(image_path: Path, file_path: Path):
    """
    1. Opens the disk image using pytsk3.Img_Info.
    2. Initializes a filesystem object (pytsk3.FS_Info).
    3. Locates the file by path.
    4. Prints out run information and detects slack.
    """
    # Open the disk/ISO image
    img = pytsk3.Img_Info(str(image_path))

    # Create a filesystem object (for partition 0 if the image is partitionless
    # or for the file system within an ISO). For multi-partition images,
    # you may need to detect/parse the partition offset via pytsk3.Volume_Info
    fs = pytsk3.FS_Info(img)

    # Obtain a pytsk3.File object for the requested path
    print(file_path.as_posix())
    file_obj = find_file_in_fs(fs, file_path.as_posix())

    # Print the cluster runs and slack information
    print_file_runs(fs, file_obj)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <image_path> <file_path_in_fs>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    file_path = Path(sys.argv[2])

    main(image_path, file_path)
