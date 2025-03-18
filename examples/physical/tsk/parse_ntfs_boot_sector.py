import pytsk3
import sys
from pathlib import Path

def parse_ntfs_boot_sector(img, offset=0):
    """Parses the NTFS boot sector."""
    fs_info = pytsk3.FS_Info(img, offset=offset)
    boot_sector = fs_info.info.fs_file.read_random(0, 512)
    
    # Parse the boot sector fields
    oem_id = boot_sector[3:11].decode('ascii')
    bytes_per_sector = int.from_bytes(boot_sector[11:13], 'little')
    sectors_per_cluster = boot_sector[13]
    reserved_sectors = int.from_bytes(boot_sector[14:16], 'little')
    media_descriptor = boot_sector[21]
    sectors_per_track = int.from_bytes(boot_sector[24:26], 'little')
    number_of_heads = int.from_bytes(boot_sector[26:28], 'little')
    hidden_sectors = int.from_bytes(boot_sector[28:32], 'little')
    total_sectors = int.from_bytes(boot_sector[40:48], 'little')
    mft_cluster_number = int.from_bytes(boot_sector[48:56], 'little')
    mft_mirror_cluster_number = int.from_bytes(boot_sector[56:64], 'little')
    clusters_per_file_record_segment = boot_sector[64]
    clusters_per_index_buffer = boot_sector[68]
    volume_serial_number = int.from_bytes(boot_sector[72:80], 'little')

    print(f"OEM ID: {oem_id}")
    print(f"Bytes per Sector: {bytes_per_sector}")
    print(f"Sectors per Cluster: {sectors_per_cluster}")
    print(f"Reserved Sectors: {reserved_sectors}")
    print(f"Media Descriptor: {media_descriptor}")
    print(f"Sectors per Track: {sectors_per_track}")
    print(f"Number of Heads: {number_of_heads}")
    print(f"Hidden Sectors: {hidden_sectors}")
    print(f"Total Sectors: {total_sectors}")
    print(f"MFT Cluster Number: {mft_cluster_number}")
    print(f"MFT Mirror Cluster Number: {mft_mirror_cluster_number}")
    print(f"Clusters per File Record Segment: {clusters_per_file_record_segment}")
    print(f"Clusters per Index Buffer: {clusters_per_index_buffer}")
    print(f"Volume Serial Number: {volume_serial_number}")

def main(image_path: Path):
    """Main function to parse the NTFS boot sector."""
    img = pytsk3.Img_Info(str(image_path))
    parse_ntfs_boot_sector(img)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <image_path>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    main(image_path)