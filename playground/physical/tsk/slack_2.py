"""
Find slack space, as well as the first unallocated space in a filesystem.
"""

import sys

import pytsk3


def print_file_runs_and_slack(fs, file_obj):
    """
    Print out the file's cluster runs, the slack space offset (if any),
    and the last allocated cluster used by the file.
    """
    fs_block_size = fs.info.block_size
    runs_info = []

    for attr in file_obj:
        # On NTFS, data attributes are TSK_FS_ATTR_TYPE_NTFS_DATA (128).
        # For other FS, TSK_FS_ATTR_TYPE_DEFAULT may apply.
        if attr.info.type in (
            pytsk3.TSK_FS_ATTR_TYPE_DEFAULT,
            pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA,
        ):
            for run in attr:
                if run.len > 0:  # 0 signals no more runs
                    runs_info.append(
                        {
                            "file_offset": run.offset,
                            "cluster_addr": run.addr,
                            "cluster_len": run.len,
                        }
                    )

    # Sort runs by their starting offset in the file
    runs_info.sort(key=lambda r: r["file_offset"])

    # Print run info
    print("File Data Runs:")
    for i, r in enumerate(runs_info, start=1):
        # Physical offset in bytes = cluster address * block_size
        physical_offset = r["cluster_addr"] * fs_block_size
        physical_length = r["cluster_len"] * fs_block_size
        print(f" Run #{i}:")
        print(
            f"   File offset range    : [{r['file_offset']}, "
            f"{r['file_offset'] + physical_length})"
        )
        print(f"   Cluster address      : {r['cluster_addr']}")
        print(f"   Clusters count       : {r['cluster_len']}")
        print(f"   Physical offset (B)  : {physical_offset}")
        print(f"   Physical length (B)  : {physical_length}")

    meta = file_obj.info.meta
    if not meta:
        print("\nNo meta information for this file.")
        return None

    actual_size = meta.size
    # Compute allocated size from the sum of run lengths times block size
    allocated_size = sum(r["cluster_len"] for r in runs_info) * fs_block_size
    print(f"\nActual file size   : {actual_size}")
    print(f"Allocated size     : {allocated_size}")

    slack_offset = None
    if allocated_size > actual_size:
        slack_size = allocated_size - actual_size
        print(f"Slack space        : {slack_size} bytes")
        # Slack starts at (top of last byte of file data)
        # Identify which run holds the last byte of file data:
        file_end = actual_size
        for r in reversed(runs_info):
            run_start = r["file_offset"]
            run_size_bytes = r["cluster_len"] * fs_block_size
            run_end = run_start + run_size_bytes
            if file_end > run_start:
                used_in_this_run = min(file_end, run_end) - run_start
                # Slack begins in this run
                slack_offset = (r["cluster_addr"] * fs_block_size) + used_in_this_run
                print(f"Slack begins at offset: {slack_offset}")
                break
    else:
        print("No slack space.")

    # Return the last allocated cluster so we can search for unallocated space after it
    if runs_info:
        highest_run = max(runs_info, key=lambda r: r["cluster_addr"] + r["cluster_len"])
        last_cluster = highest_run["cluster_addr"] + highest_run["cluster_len"] - 1
        return last_cluster
    return None


def find_first_unallocated_cluster(fs):
    """
    Finds the first unallocated cluster in the filesystem.
    """
    print(f"{fs.info.block_count=}")
    end_block = fs.info.block_count - 1

    for block_num in range(0, end_block + 1):
        try:
            block_meta = fs.open_meta(block_num)
            if block_meta.info.meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC:
                return block_num
        except IOError:
            continue

    return None


def find_file_in_fs(fs, path_to_file):
    """Open the specified file by path and return a pytsk3.File object."""
    try:
        return fs.open(path=path_to_file)
    except IOError:
        print(f"Could not open file: {path_to_file}")
        sys.exit(1)


def main(image_path, file_path):
    # 1. Open the disk/ISO image
    img = pytsk3.Img_Info(image_path)
    # 2. Prepare filesystem object
    fs = pytsk3.FS_Info(img)

    # 3. Open the file in question
    file_obj = find_file_in_fs(fs, file_path)

    # 4. Print info about runs, slack space, and get the last allocated cluster
    last_cluster = print_file_runs_and_slack(fs, file_obj)

    # 5. Find the first unallocated cluster in the filesystem
    first_unalloc_cluster = find_first_unallocated_cluster(fs)
    if first_unalloc_cluster is not None:
        block_size = fs.info.block_size
        physical_start = first_unalloc_cluster * block_size
        print(f"\nFirst unallocated cluster:")
        print(f"  Cluster number   : {first_unalloc_cluster}")
        print(f"  Physical offset  : {physical_start} bytes")
    else:
        print("\nNo unallocated clusters found in the filesystem.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <image_path> <file_path_in_fs>")
        sys.exit(1)

    image_path = sys.argv[1]
    file_path = sys.argv[2]
    main(image_path, file_path)
