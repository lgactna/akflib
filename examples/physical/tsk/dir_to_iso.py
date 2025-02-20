"""
Prompts:
- Can you write a Python script that gives me an example usage of the pytsk3 
  library to load a .iso file and walk through the underlying filesystem?
- Can you modify this script so that it instead accepts a path to a folder, uses 
  pycdlib to construct a valid filesystem on an ISO file, and then uses 
  pytsk3 to walk the resulting ISO file?
"""

import sys
from pathlib import Path

import pycdlib
import pytsk3

# def create_iso_from_folder(folder_path: str, iso_path: str) -> None:
#     """
#     Creates an ISO-9660 image from the contents of 'folder_path' using pycdlib,
#     writing the result to 'iso_path'.
#     """
#     iso = pycdlib.PyCdlib()

#     # Initialize a new ISO-9660 filesystem; Joliet extensions are enabled.
#     iso.new(joliet=True)

#     # Recursively add files and subdirectories from the folder
#     for root, dirs, files in os.walk(folder_path):
#         for d in dirs:
#             # Convert paths into ISO-9660-compliant directory names
#             rel_dir_path = os.path.relpath(os.path.join(root, d), folder_path)

#             iso.add_directory(joliet_path="/"+rel_dir_path.replace(os.sep, "/"))
#         for f in files:
#             rel_file_path = os.path.relpath(os.path.join(root, f), folder_path)
#             iso.add_file(
#                 os.path.join(root, f),
#                 joliet_path="/"+rel_file_path.replace(os.sep, "/"),
#             )
#     # Write out the ISO file
#     iso.write(iso_path)
#     iso.close()


def create_iso_from_folder(folder_path: Path, iso_path: Path) -> None:
    """
    Creates an ISO-9660 image from the contents of 'folder_path' using pycdlib,
    writing the result to 'iso_path'.
    """
    iso = pycdlib.PyCdlib()
    iso.new(joliet=True)

    # Recursively add files and subdirectories
    for item in folder_path.rglob("*"):
        # Get relative path of item from folder (using forward slashes). This
        # will be placed relative to the root of the ISO filesystem and therefore
        # must start with a leading "/".
        relative_path = "/" + item.relative_to(folder_path).as_posix()

        # Add to ISO.
        if item.is_dir():
            iso.add_directory(joliet_path=relative_path)
        else:
            iso.add_file(str(item), joliet_path=relative_path)

    # Write ISO to specified path.
    iso.write(str(iso_path.resolve()))
    iso.close()


def print_directory(directory, indent=0) -> None:
    for entry in directory:
        if entry.info.name.name in [b".", b".."]:
            continue
        print(" " * indent + entry.info.name.name.decode("utf-8"))
        if entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
            sub_directory = entry.as_directory()
            print_directory(sub_directory, indent + 2)


def main(folder_path: Path, iso_path: Path) -> None:
    # Create ISO from folder with pycdlib (ISO-9660)
    create_iso_from_folder(folder_path, iso_path)

    # Use pytsk3 to open and walk the generated ISO file
    img = pytsk3.Img_Info(str(iso_path))
    fs = pytsk3.FS_Info(img)
    root_dir = fs.open_dir("/")
    print_directory(root_dir)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <folder_path> <output_iso_path>")
        sys.exit(1)

    folder_path = Path(sys.argv[1])
    iso_path = Path(sys.argv[2])
    main(folder_path, iso_path)
