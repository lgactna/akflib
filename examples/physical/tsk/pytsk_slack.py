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
    
    # tsk_fs_file.meta -> tsk_fs_meta.attr -> tsk_fs_attrlist.head
    # -> tsk_fs_attr.run -> tsk_fs_attr_run.addr, len, offset
    # https://sleuthkit.org/sleuthkit/docs/api-docs/4.10.0/structTSK__FS__ATTR__RUN.html

    for attr in file_obj:
        # On NTFS, data attributes are often TSK_FS_ATTR_TYPE_NTFS_DATA (128);
        # for other FS, TSK_FS_ATTR_TYPE_DEFAULT may apply.
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
                            # This one is incorrect, run.offset is also in
                            # block size, not bytes as implied here
                            "run_offset_in_file": run.offset * fs_block_size,
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

    actual_size = meta.size
    allocated_size = sum(r["physical_len"] for r in runs_info)

    print(f"\nActual size: {actual_size} bytes")
    print(f"Allocated size: {allocated_size} bytes")

    if allocated_size <= actual_size:
        print("No slack space.")
        return

    slack_size = allocated_size - actual_size
    print(f"Slack space: {slack_size} bytes")

    # Identify where slack begins in the last run containing file data
    file_end = actual_size
    for info in reversed(runs_info):
        start_of_run = info["run_offset_in_file"]
        end_of_run = start_of_run + info["physical_len"]
        if file_end > start_of_run:
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
    1. Opens the disk/ISO image using pytsk3.Img_Info.
    2. Enumerates partitions via pytsk3.Volume_Info and prompts user to select one.
    3. Creates a pytsk3.FS_Info for the selected partition.
    4. Locates the file by path and prints out run/slack info.
    """
    # Open the image
    img = pytsk3.Img_Info(str(image_path))

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

    print(f"\nAnalyzing file: {file_path.as_posix()}")
    file_obj = find_file_in_fs(fs, file_path.as_posix())
    print_file_runs(fs, file_obj)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <image_path> <file_path_in_fs>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    file_path = Path(sys.argv[2])

    main(image_path, file_path)