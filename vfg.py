import json
import asyncio
import multiprocessing
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from playwright.async_api import async_playwright


# ==============================
# MACHINE CONFIG
# ==============================

TOTAL_CORES = multiprocessing.cpu_count()

MAX_WORKERS = 3
WIDTH, HEIGHT = 1920, 1080
FPS = 30

BASE_MODULES_PATH = Path("modules")

INTRO_VIDEO = "intro_v0.mp4"
END_VIDEO = "end_v0.mp4"

print("CPU cores:", TOTAL_CORES)


# ==============================
# HTML TEMPLATE
# ==============================

def get_content_html(title, markdown_text):

    bullets = ""

    for line in markdown_text.split("\n"):
        if line.strip():
            clean = line.strip().lstrip("- ").lstrip("* ")
            bullets += f"<li>{clean}</li>"

    return f"""
    <html>
    <body style="background:black;color:white;width:{WIDTH}px;height:{HEIGHT}px;font-family:sans-serif;padding:120px">
        <h1 style="font-size:70px">{title}</h1>
        <ul style="font-size:40px">{bullets}</ul>
    </body>
    </html>
    """


def get_intro_html(chapter, module):

    return f"""
    <html>
    <body style="background:black;color:white;width:{WIDTH}px;height:{HEIGHT}px;font-family:sans-serif;text-align:center;padding-top:300px">
        <h1 style="font-size:80px">{chapter}</h1>
        <h2 style="font-size:50px">{module}</h2>
    </body>
    </html>
    """


# ==============================
# SLIDE GENERATOR
# ==============================

async def generate_slides(chunk_file, timeline_file, slides_dir):

    with open(chunk_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    with open(timeline_file, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    slides_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:

        browser = await p.chromium.launch()

        page = await browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})

        await page.set_content(
            get_intro_html(meta["chapter_title"], meta["module_title"])
        )

        await page.screenshot(path=str(slides_dir / "slide_intro.png"))

        for i, segment in enumerate(timeline):

            await page.set_content(
                get_content_html(
                    segment["display"]["title"],
                    segment["display"]["markdown"]
                )
            )

            await page.screenshot(
                path=str(slides_dir / f"slide_{i}.png")
            )

        await browser.close()


# ==============================
# FFmpeg segment builder
# ==============================

def render_segment(slide, audio, out):

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", slide,
        "-i", audio,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-r", str(FPS),
        out
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ==============================
# MODULE VIDEO BUILDER
# ==============================

def assemble_module_video(timeline_file, slides_dir, output_path):

    with open(timeline_file, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    temp_segments = []

    for i, seg in enumerate(timeline):

        audio = Path(seg["file"].replace("\\", "/")).resolve()

        slide = slides_dir / f"slide_{i}.png"

        if not audio.exists() or not slide.exists():
            continue

        out = slides_dir / f"seg_video_{i}.mp4"

        render_segment(str(slide), str(audio), str(out))

        temp_segments.append(out)

    # concat list file

    concat_file = slides_dir / "concat.txt"

    with open(concat_file, "w") as f:
        for seg in temp_segments:
            f.write(f"file '{seg.resolve()}'\n")

    main_video = slides_dir / "module_content.mp4"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(main_video)
    ])

    # final video with intro/end

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", INTRO_VIDEO,
        "-i", str(main_video),
        "-i", END_VIDEO,
        "-filter_complex",
        "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1",
        "-pix_fmt", "yuv420p",
        output_path
    ])


# ==============================
# MODULE WORKER
# ==============================

def process_module(chunk_file):

    chapter_dir = chunk_file.parents[1]

    module_name = chunk_file.stem.replace("_chunks", "")

    slides_dir = chapter_dir / f"slides_{module_name}"

    audio_dir = chapter_dir / "audio" / module_name

    timeline_file = audio_dir / "timeline.json"

    output_video = chapter_dir / f"{chapter_dir.name}_{module_name}.mp4"

    if output_video.exists():
        print("Skipping:", output_video)
        return

    asyncio.run(
        generate_slides(chunk_file, timeline_file, slides_dir)
    )

    assemble_module_video(
        timeline_file,
        slides_dir,
        str(output_video)
    )

    print("Rendered:", output_video)


# ==============================
# CHAPTER MERGE
# ==============================

def assemble_full_chapter_video(chapter_dir):

    output = chapter_dir / f"{chapter_dir.name}_full.mp4"

    if output.exists():
        return

    modules = sorted(
        chapter_dir.glob(f"{chapter_dir.name}_m*.mp4")
    )

    if not modules:
        return

    concat_file = chapter_dir / "chapter_concat.txt"

    with open(concat_file, "w") as f:

        f.write(f"file '{Path(INTRO_VIDEO).resolve()}'\n")

        for m in modules:
            f.write(f"file '{m.resolve()}'\n")

        f.write(f"file '{Path(END_VIDEO).resolve()}'\n")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output)
    ])

    print("Chapter video:", output)


# ==============================
# CONTROLLER
# ==============================

def run_parallel():

    chapters = sorted([c for c in BASE_MODULES_PATH.iterdir() if c.is_dir()])

    jobs = []

    for chapter in chapters:

        chunk_files = sorted(
            chapter.rglob("chunks/m*_chunks.json")
        )

        jobs.extend(chunk_files)

    print("Modules:", len(jobs))

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_module, jobs)

    for chapter in chapters:
        assemble_full_chapter_video(chapter)


# ==============================
# START
# ==============================

if __name__ == "__main__":

    print("\nFFmpeg Video Pipeline Started\n")

    run_parallel()

    print("\nAll videos completed\n")