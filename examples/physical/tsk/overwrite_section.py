from pathlib import Path
import sys


def overwrite_section(file_path: Path, offset: int, data: bytes):
    with open(file_path, 'r+b') as f:
        f.seek(offset)
        f.write(data)
        
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <file_to_overwrite> <offset (int, base 10)> <file_to_insert>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    offset = int(sys.argv[2])
    
    with open(sys.argv[3], 'rb') as f:
        data = f.read()

    overwrite_section(file_path, offset, data)
    