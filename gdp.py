import json
from pathlib import Path

BASE = Path("modules")

S3_BASE = "https://srinivas-ias-academy.s3.amazonaws.com/GPSTR/Courses/Social/AncientHistory"

data = {
    "course": "GPSTR Social Ancient History",
    "chapters": []
}

for chapter in sorted(BASE.iterdir()):

    if not chapter.is_dir():
        continue

    chapter_name = chapter.name

    chapter_data = {
        "chapter_name": chapter_name,
        "chapter_video": f"{S3_BASE}/{chapter_name}/{chapter_name}_full.mp4",
        "modules": []
    }

    for video in sorted(chapter.glob(f"{chapter_name}_m*.mp4")):

        module = video.stem.split("_")[-1]

        module_data = {
            "module_name": module,
            "video": f"{S3_BASE}/{chapter_name}/{video.name}",
            "thumbnail": f"{S3_BASE}/{chapter_name}/{chapter_name}_{module}_thumb.png"
        }

        chapter_data["modules"].append(module_data)

    data["chapters"].append(chapter_data)

with open("course_data.json", "w") as f:
    json.dump(data, f, indent=2)

print("course_data.json created")