from pathlib import Path

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "question_sources"

SPLITS = (
    {
        "source": "AWS Certified AI Practitioner AIF-C01_aizh (2).pdf",
        "output": "AWS Certified AI Practitioner AIF-C01_with_aizh_part_{part:02d}.pdf",
        "ranges": (
            (1, 74),
            (75, 148),
            (149, 216),
            (217, 290),
            (291, 368),
            (369, 450),
            (451, 533),
            (534, 621),
            (622, 712),
            (713, 803),
        ),
    },
    {
        "source": "AWS Certified AI Practitioner AIF-C01_en_with_discussion.pdf",
        "output": "AWS Certified AI Practitioner AIF-C01_with_discussion_part_{part:02d}.pdf",
        "ranges": (
            (1, 92),
            (93, 164),
            (165, 227),
            (228, 282),
            (283, 334),
            (335, 382),
            (383, 432),
            (433, 480),
            (481, 526),
            (527, 576),
        ),
    },
)


for split in SPLITS:
    source = SOURCE_DIR / split["source"]
    reader = PdfReader(source)
    expected_pages = split["ranges"][-1][1]
    if len(reader.pages) != expected_pages:
        raise RuntimeError(
            f"{source.name}: expected {expected_pages} pages, found {len(reader.pages)}"
        )

    for part, (start_page, end_page) in enumerate(split["ranges"], start=1):
        writer = PdfWriter()
        for page_index in range(start_page - 1, end_page):
            writer.add_page(reader.pages[page_index])

        output = SOURCE_DIR / split["output"].format(part=part)
        with output.open("wb") as stream:
            writer.write(stream)
        print(f"{output.name}: pages {start_page}-{end_page} ({end_page - start_page + 1})")
