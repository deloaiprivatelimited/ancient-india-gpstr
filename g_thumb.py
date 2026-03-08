import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# ==============================
# CONFIG
# ==============================

WIDTH = 1920
HEIGHT = 1080

BASE_MODULES_PATH = Path("modules")

print("🖼 Thumbnail Generator Started")


# ==============================
# HTML TEMPLATE
# ==============================


def get_thumbnail_html(chapter_title, module_title):
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;800&family=Noto+Sans+Kannada:wght@700&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                width: {WIDTH}px;
                height: {HEIGHT}px;
                background: radial-gradient(circle at 70% 40%, #001a25 0%, #020202 70%);
                font-family: 'Inter', 'Noto Sans Kannada', sans-serif;
                color: white;
                display: flex;
                flex-direction: column;
                justify-content: center;
                padding-left: 180px;
                overflow: hidden;
            }}

            .brand {{
                position: absolute;
                top: 70px;
                right: 120px;
                font-size: 24px;
                letter-spacing: 4px;
                color: #00c6ff;
            }}

            .class-tag {{
                font-size: 28px;
                color: #00c6ff;
                border: 2px solid #00c6ff;
                padding: 8px 35px;
                border-radius: 50px;
                display: inline-block;
                margin-bottom: 40px;
            }}

            .chapter-title {{
                font-size: 110px;
                font-weight: 800;
                line-height: 1.1;
                max-width: 1400px;
            }}

            .module-title {{
                font-size: 55px;
                color: #cccccc;
                margin-top: 35px;
                font-weight: 600;
            }}

            .accent-line {{
                width: 180px;
                height: 6px;
                background: #00c6ff;
                margin-top: 50px;
                border-radius: 3px;
                box-shadow: 0 0 25px rgba(0, 198, 255, 0.6);
            }}
        </style>
    </head>
    <body>

        <div class="brand">SRINIVAS IAS ACADEMY</div>

        <div class="class-tag">8ನೇ ತರಗತಿ ಸಮಾಜ ವಿಜ್ಞಾನ</div>

        <div class="chapter-title">{chapter_title}</div>

        <div class="module-title">{module_title}</div>

        <div class="accent-line"></div>

    </body>
    </html>
    """


# ==============================
# GENERATE THUMBNAIL
# ==============================

async def generate_thumbnail(meta_file, output_path):

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    chapter_title = meta.get("chapter_title", "Chapter")
    module_title = meta.get("module_title", "Module")

    async with async_playwright() as p:

        browser = await p.chromium.launch()

        page = await browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT}
        )

        await page.set_content(
            get_thumbnail_html(chapter_title, module_title)
        )

        await page.screenshot(path=str(output_path))

        await browser.close()

    print("✅ Thumbnail:", output_path.name)


# ==============================
# MAIN
# ==============================

async def main():

    chapters = sorted([
        c for c in BASE_MODULES_PATH.iterdir()
        if c.is_dir()
    ])

    for chapter in chapters:

        chunks_path = chapter / "chunks"

        if not chunks_path.exists():
            continue

        for meta_file in sorted(chunks_path.glob("m*_chunks.json")):

            module_name = meta_file.stem.replace("_chunks", "")

            output_path = chapter / f"{chapter.name}_{module_name}_thumb.png"

            if output_path.exists():
                print("⏭ Skipping:", output_path.name)
                continue

            await generate_thumbnail(meta_file, output_path)


# ==============================
# START
# ==============================

if __name__ == "__main__":

    asyncio.run(main())

    print("🎉 All thumbnails generated")