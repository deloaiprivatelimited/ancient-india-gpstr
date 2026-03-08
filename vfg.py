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
            clean_line = line.strip().lstrip('- ').lstrip('* ')
            bullets += f"<li><span class='bullet-node'></span>{clean_line}</li>"

    return f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Noto+Sans+Kannada:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
            width: {WIDTH}px;
            height: {HEIGHT}px;
            background-color: #020202;
            /* Subtle glow behind the content area on the right */
            background-image: radial-gradient(circle at 80% 50%, #001a25 0%, #020202 70%);
            font-family: 'Inter', 'Noto Sans Kannada', sans-serif;
            color: #ffffff;
            display: flex;
            overflow: hidden;
        }}

        /* Left Side: Fixed Branding Pillar */
        .sidebar {{
            width: 500px;
            height: 100%;
            display: flex;
            align-items: flex-start;
            padding-left: 80px;
            padding-top: 100px;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .brand-name {{
            font-size: 24px;
            font-weight: 600;
            letter-spacing: 5px;
            color: #00c6ff;
            text-transform: uppercase;
            border-left: 3px solid #00c6ff;
            padding-left: 20px;
            line-height: 1;
        }}

        /* Right Side: Content Area */
        .content-area {{
            flex-grow: 1;
            padding: 100px 100px 100px 80px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        .title {{
            font-size: 72px;
            font-weight: 800;
            margin-bottom: 25px;
            line-height: 1.2;
            color: #ffffff;
            max-width: 1100px;
        }}

        .accent-line {{
            width: 120px;
            height: 5px;
            background: #00c6ff;
            margin-bottom: 60px;
            border-radius: 2px;
            box-shadow: 0 0 20px rgba(0, 198, 255, 0.5);
        }}

        ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}

        li {{
            font-size: 42px;
            line-height: 1.5;
            margin-bottom: 40px;
            display: flex;
            align-items: flex-start;
            color: #cfcfcf;
            font-weight: 400;
        }}

        .bullet-node {{
            width: 8px;
            height: 28px;
            background: #00c6ff;
            margin-top: 18px;
            margin-right: 30px;
            flex-shrink: 0;
            border-radius: 1px;
        }}
    </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="brand-name">SRINIVAS IAS ACADEMY</div>
        </div>
        
        <div class="content-area">
            <div class="title">{title}</div>
            <div class="accent-line"></div>
            
            <ul>
                {bullets}
            </ul>
        </div>
    </body>
    </html>
    """

def get_intro_html(chapter, module):
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ margin:0; background:#020202; color:white; font-family:'Noto Sans Kannada', sans-serif; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; width:{WIDTH}px; height:{HEIGHT}px; background-image: radial-gradient(circle at 50% 50%, #001a25 0%, #020202 80%); }}
            .tag {{ font-size: 30px; color: #00c6ff; border: 2px solid #00c6ff; padding: 10px 40px; border-radius: 50px; margin-bottom: 40px; }}
            .chapter {{ font-size: 80px; font-weight: 800; max-width: 1500px; line-height: 1.2; }}
            .bar {{ width: 300px; height: 4px; background: linear-gradient(90deg, transparent, #00c6ff, transparent); margin: 50px 0; }}
            .module {{ font-size: 45px; color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="tag">8ನೇ ತರಗತಿ ಸಮಾಜ ವಿಜ್ಞಾನ</div>
        <div class="chapter">{chapter}</div>
        <div class="bar"></div>
        <div class="module">{module}</div>
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