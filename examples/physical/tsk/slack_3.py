"""
Find unallocated space immediately after a provided file.
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


def find_unallocated_space_after(fs, last_cluster):
    """
    Finds the next unallocated cluster after 'last_cluster'
    and measures how many consecutive unallocated clusters there are.
    """
    if last_cluster is None:
        print("No allocated clusters found; cannot search for unallocated space.")
        return

    # We walk from (last_cluster + 1) to the end of the filesystem
    # looking for unallocated blocks. We collect consecutive runs.
    start_block = last_cluster + 1
    end_block = fs.info.block_count - 1

    consecutive_count = 0
    first_unalloc_block = None
    current_block = None

    # We'll do a simple pass collecting the longest consecutive unallocated region
    # that starts at or after 'last_cluster + 1'.
    longest_region_start = None
    longest_region_length = 0
    in_region = False
    region_start = 0
    region_length = 0

    for block_num in range(start_block, end_block + 1):
        try:
            block_meta = fs.open_meta(block_num)
            if block_meta.info.meta.flags & pytsk3.TSK_FS_META_FLAG_UNALLOC:
                current_block = block_num
                if not in_region:
                    # Start a new region
                    in_region = True
                    region_start = current_block
                    region_length = 1
                else:
                    # Continue region if consecutive
                    if current_block == region_start + region_length:
                        region_length += 1
                    else:
                        # Region ended; save if it's the longest so far
                        if region_length > longest_region_length:
                            longest_region_length = region_length
                            longest_region_start = region_start
                        # Start a new region
                        region_start = current_block
                        region_length = 1
            else:
                in_region = False
        except IOError:
            continue

    # Check the very end if we ended in a region
    if in_region and region_length > longest_region_length:
        longest_region_length = region_length
        longest_region_start = region_start

    if longest_region_start is not None:
        block_size = fs.info.block_size
        physical_start = longest_region_start * block_size
        physical_len = longest_region_length * block_size
        print(f"\nNext unallocated region after cluster {last_cluster}:")
        print(f"  Start cluster    : {longest_region_start}")
        print(f"  Length (clusters): {longest_region_length}")
        print(f"  Physical offset  : {physical_start}")
        print(f"  Physical length  : {physical_len} bytes")
    else:
        print("\nNo unallocated space found after the last file cluster.")


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

    # 5. Find next unallocated space after the file’s last cluster
    find_unallocated_space_after(fs, last_cluster)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <image_path> <file_path_in_fs>")
        sys.exit(1)

    image_path = sys.argv[1]
    file_path = sys.argv[2]
    main(image_path, file_path)
