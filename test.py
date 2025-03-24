import logging
from pathlib import Path

from akflib.core.disk.core import get_file_entry, open_file_system
from akflib.core.disk.slack import analyze_file_slack, insert_into_file_slack

logging.basicConfig(level=logging.DEBUG)


def test_slack() -> None:
    # Sample: writing to slack space of a file

    # Test writing to slack space, based on the example in the playground folder
    image_path = Path("C:\\Users\\Kisun\\Downloads\\decrypted-2.iso")
    data = b"Hello, world!"
    location = "Users\\user\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\agent.exe"

    # Open the filesystem, select largest partition by default
    fs, volume_info = open_file_system(image_path)

    # Get the file entry
    file_entry = get_file_entry(fs, location)
    # Analyze the slack space of the file
    meta = analyze_file_slack(file_entry, volume_info.volume_extent_offset)

    # Write data to slack space
    insert_into_file_slack(image_path, data, meta)


def test_rendering() -> None:
    # Sample: UCO bundle rendering
    # from akflib.rendering.core import render_uco_bundle
    pass
