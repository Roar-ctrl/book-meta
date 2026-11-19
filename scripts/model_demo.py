"""Прогон модельной части на PDF: формулы -> LaTeX, плюс отладочные картинки с рамками.

    python scripts/model_demo.py book.pdf --pages 10-20 -o out.json --debug-dir debug
    python scripts/model_demo.py book.pdf --layout-model PP-DocLayout-M --threads 4

В debug-картинках: красные рамки — формулы, прошедшие правила; синие — убранные правилами (с именем правила);
серые — остальные регионы. В JSON для каждой формулы видно сырой вывод модели, сработавшие правила и проблемы.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import ImageDraw  # noqa: E402

from book_meta.extractors.formulas.image_model import recognize_formulas  # noqa: E402
from book_meta.extractors.formulas.recognizers import get_recognizer  # noqa: E402
from book_meta.readers.layout_paddle import PaddleLayout  # noqa: E402
from book_meta.utils.paddle_runtime import PaddleSettings  # noqa: E402
from book_meta.utils.render import get_renderer  # noqa: E402


def parse_pages(spec, n):
    if not spec:
        return None
    pages = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        pages.update(range(int(a), int(b or a) + 1))
    return sorted(p - 1 for p in pages if 1 <= p <= n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="model_demo.json")
    ap.add_argument("--pages", help="1-based: '3', '5-9', '1,4,7-8'")
    ap.add_argument("--debug-dir")
    ap.add_argument("--include-inline", action="store_true")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--layout-model")
    ap.add_argument("--formula-model")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    overrides = {k: v for k, v in {
        "device": args.device, "cpu_threads": args.threads,
        "layout_model": args.layout_model, "formula_model": args.formula_model,
    }.items() if v}
    s = PaddleSettings(**overrides)
    renderer = get_renderer()
    layout = PaddleLayout(s, renderer)
    pages = parse_pages(args.pages, renderer.page_count(args.pdf))

    run = recognize_formulas(
        args.pdf, layout=layout, recognizer=get_recognizer("paddle", s), renderer=renderer,
        settings=s, include_inline=args.include_inline, pages=pages,
    )

    result = [{
        "page": f.page_index + 1,
        "bbox": f.bbox.model_dump(),
        "latex": f.latex, "raw_latex": f.raw_latex,
        "confidence": f.confidence, "layout_confidence": round(f.layout_confidence, 3),
        "issues": f.issues, "rules": [f"{h.rule}: {h.detail}" for h in f.hits],
    } for f in run.formulas]
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(result)} формул -> {args.out}")

    if args.debug_dir:
        out_dir = Path(args.debug_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        all_regions = layout.regions(args.pdf, pages)   # повторный прогон layout только ради картинок
        for page in sorted({r.page_index for r in all_regions}):
            img = renderer.render_page(args.pdf, page, s.layout_dpi)
            w, h = img.size
            draw = ImageDraw.Draw(img)
            box = lambda r: (r.bbox.x0 * w, r.bbox.y0 * h, r.bbox.x1 * w, r.bbox.y1 * h)  # noqa: E731
            for r in all_regions:
                if r.page_index == page:
                    draw.rectangle(box(r), outline="gray", width=1)
            for hit in run.region_hits.get(page, []):
                for r in hit.removed:
                    draw.rectangle(box(r), outline="blue", width=3)
                    draw.text((r.bbox.x0 * w + 3, r.bbox.y0 * h + 3), hit.rule, fill="blue")
            for f in run.formulas:
                if f.page_index == page:
                    draw.rectangle((f.bbox.x0 * w, f.bbox.y0 * h, f.bbox.x1 * w, f.bbox.y1 * h), outline="red", width=3)
            img.save(out_dir / f"page_{page + 1:04d}.png")


if __name__ == "__main__":
    main()
