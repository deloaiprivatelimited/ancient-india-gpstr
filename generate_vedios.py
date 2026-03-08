import json
import asyncio
import multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from moviepy import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips
from playwright.async_api import async_playwright

# ==============================
# MACHINE CONFIG
# ==============================

TOTAL_CORES = multiprocessing.cpu_count()

MAX_WORKERS = 3
THREADS_PER_JOB = 4

FPS = 30
WIDTH, HEIGHT = 1920, 1080

CRF_VALUE = "23"
PRESET = "ultrafast"

BASE_MODULES_PATH = Path("modules")

INTRO_VIDEO = "intro_v0.mp4"
END_VIDEO = "end_v0.mp4"

print("CPU:", TOTAL_CORES)

# ==============================
# HTML TEMPLATES
# ==============================

def get_content_html(title, markdown_text):

    bullets = ""

    for line in markdown_text.split("\n"):
        if line.strip():
            clean_line = line.strip().lstrip("- ").lstrip("* ")
            bullets += f"<li>{clean_line}</li>"

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
# SLIDE GENERATION
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

        # intro slide

        await page.set_content(
            get_intro_html(meta["chapter_title"], meta["module_title"])
        )

        await page.screenshot(path=str(slides_dir / "slide_intro.png"))

        # content slides

        for i, segment in enumerate(timeline):

            await page.set_content(
                get_content_html(
                    segment["display"]["title"],
                    segment["display"]["markdown"]
                )
            )

            await page.screenshot(path=str(slides_dir / f"slide_{i}.png"))

        await browser.close()


# ==============================
# VIDEO BUILDER
# ==============================

def assemble_video(timeline_file, slides_dir, output_path):

    print("Building video:", output_path)

    with open(timeline_file, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    clips = []

    # intro slide

    clips.append(
        ImageClip((slides_dir / "slide_intro.png").as_posix())
        .with_duration(4)
        .with_fps(FPS)
    )

    # content slides

    for i, segment in enumerate(timeline):

        audio_path = Path(segment["file"]).resolve()

        slide_path = slides_dir / f"slide_{i}.png"

        print("Audio:", audio_path)
        print("Slide:", slide_path)

        if not audio_path.exists():
            print("Missing audio:", audio_path)
            continue

        if not slide_path.exists():
            print("Missing slide:", slide_path)
            continue

        audio = AudioFileClip(audio_path.as_posix())

        clip = (
            ImageClip(slide_path.as_posix())
            .with_duration(audio.duration)
            .with_audio(audio)
            .with_fps(FPS)
        )

        clips.append(clip)

    main_video = concatenate_videoclips(clips, method="compose")

    final = concatenate_videoclips(
        [
            VideoFileClip(INTRO_VIDEO).resized((WIDTH, HEIGHT)),
            main_video,
            VideoFileClip(END_VIDEO).resized((WIDTH, HEIGHT))
        ],
        method="compose"
    )

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset=PRESET,
        threads=THREADS_PER_JOB,
        ffmpeg_params=["-crf", CRF_VALUE]
    )


# ==============================
# MODULE WORKER
# ==============================

def process_module(chunk_file):

    # correct chapter dir

    chapter_dir = chunk_file.parents[1]

    module_name = chunk_file.stem.replace("_chunks", "")

    print("Processing:", chunk_file)

    slides_dir = chapter_dir / f"slides_{module_name}"

    audio_dir = chapter_dir / "audio" / module_name

    timeline_file = audio_dir / "timeline.json"

    output_video = chapter_dir / f"{chapter_dir.name}_{module_name}.mp4"

    if output_video.exists():
        print("Skipping existing:", output_video.name)
        return

    if not timeline_file.exists():
        print("Missing timeline:", timeline_file)
        return

    print("Generating slides...")

    asyncio.run(
        generate_slides(chunk_file, timeline_file, slides_dir)
    )

    assemble_video(
        timeline_file,
        slides_dir,
        output_video.as_posix()
    )

    print("Done:", output_video)


# ==============================
# CHAPTER MERGE
# ==============================

def assemble_full_chapter_video(chapter_dir):

    output = chapter_dir / f"{chapter_dir.name}_full.mp4"

    if output.exists():
        print("Chapter already done:", output.name)
        return

    module_videos = sorted(
        chapter_dir.glob(f"{chapter_dir.name}_m*.mp4")
    )

    if not module_videos:
        print("No modules for:", chapter_dir)
        return

    clips = []

    clips.append(VideoFileClip(INTRO_VIDEO))

    for mv in module_videos:
        clips.append(VideoFileClip(mv.as_posix()))

    clips.append(VideoFileClip(END_VIDEO))

    final = concatenate_videoclips(clips)

    final.write_videofile(
        output.as_posix(),
        fps=FPS,
        codec="libx264",
        audio_codec="aac"
    )

    print("Chapter video ready:", output)


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

        for cf in chunk_files:
            jobs.append(cf)

    print("Modules found:", len(jobs))

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_module, jobs)

    print("Module rendering finished")

    for chapter in chapters:
        assemble_full_chapter_video(chapter)


# ==============================
# START
# ==============================

if __name__ == "__main__":

    print("Video builder started")

    run_parallel()

    print("All videos completed")