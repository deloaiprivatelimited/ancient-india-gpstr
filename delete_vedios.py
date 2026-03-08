from pathlib import Path

BASE = Path("modules")

deleted = 0

for mp4 in BASE.rglob("*.mp4"):
    print("Deleting:", mp4)
    mp4.unlink()
    deleted += 1

print("\nTotal deleted:", deleted)