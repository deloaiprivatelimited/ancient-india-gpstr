from pathlib import Path

BASE_DIR = Path("modules")

def main():

    chunk_files = list(BASE_DIR.rglob("chunks/m*_chunks.json"))
    module_videos = list(BASE_DIR.rglob("*_m*.mp4"))
    chapter_videos = list(BASE_DIR.rglob("*_full.mp4"))

    total_modules = len(chunk_files)
    completed_modules = len(module_videos)
    pending_modules = total_modules - completed_modules

    print("\n==============================")
    print("📊 VIDEO BUILD PROGRESS")
    print("==============================\n")

    print(f"Total Modules Expected : {total_modules}")
    print(f"Modules Completed      : {completed_modules}")
    print(f"Modules Pending        : {pending_modules}")

    print(f"\nChapter Videos Created : {len(chapter_videos)}")

    print("\n==============================")
    print("🎬 CHAPTER VIDEOS")
    print("==============================\n")

    if not chapter_videos:
        print("None\n")
    else:
        for v in sorted(chapter_videos):
            print(v.resolve())

    print("\n==============================")
    print("📦 MODULE VIDEOS")
    print("==============================\n")

    if not module_videos:
        print("None\n")
    else:
        for v in sorted(module_videos):
            print(v.resolve())

    print("\n==============================")
    print("📁 MODULES PENDING")
    print("==============================\n")

    rendered_names = {v.stem for v in module_videos}

    for chunk in sorted(chunk_files):

        module_name = chunk.stem.replace("_chunks", "")
        chapter = chunk.parent.parent.name

        expected_name = f"{chapter}_{module_name}"

        if expected_name not in rendered_names:
            print(chunk.resolve())

    print("\n✅ Scan complete.\n")


if __name__ == "__main__":
    main()