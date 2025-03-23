import sys

import pytsk3


def list_files_in_directory(fs, directory):
    """
    Recursively list files in a directory.
    """
    for entry in directory:
        if entry.info.name.name in [b".", b".."]:
            continue
        print(entry.info.name.name.decode("utf-8"))
        if entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
            sub_directory = entry.as_directory()
            list_files_in_directory(fs, sub_directory)


def main(image_path):
    # Open the virtual hard drive image
    img = pytsk3.Img_Info(image_path)

    # Open the volume (partition) information
    vol = pytsk3.Volume_Info(img)

    # Iterate through partitions and try to open the filesystem
    for partition in vol:
        print(
            f"Partition: {partition.addr}, Start: {partition.start}, Length: {partition.len}, Description: {partition.desc.decode('utf-8')}"
        )
        try:
            fs = pytsk3.FS_Info(img, offset=partition.start * 512)
            print("Filesystem found!")
            break
        except Exception as e:
            print(f"Cannot open filesystem on partition {partition.addr}: {e}")
            fs = None

    if fs is None:
        print("No valid filesystem found in the image.")
        return

    # Open the root directory
    root_dir = fs.open_dir("/")

    # List files in the root directory
    list_files_in_directory(fs, root_dir)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path_to_vhd>")
        sys.exit(1)

    image_path = sys.argv[1]
    main(image_path)
