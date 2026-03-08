from pathlib import Path

BASE = Path("modules")

deleted = 0

for mp4 in BASE.rglob("*.mp4"):

    size = mp4.stat().st_size / (1024*1024)

    if size < 5:   # very small video → broken render
        print("Deleting bad video:", mp4, f"{size:.2f} MB")
        mp4.unlink()
        deleted += 1

print()
print("Total deleted:", deleted)