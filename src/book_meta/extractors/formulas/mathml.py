import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from xml.etree import ElementTree

MATHML_NS = "http://www.w3.org/1998/Math/MathML"
MATHML_PREFIX = f"{{{MATHML_NS}}}"


def mathml_to_latex(mathml: str, *, pandoc: str | Path = "pandoc") -> str | None:
    return mathml_to_latex_batch([mathml], pandoc=pandoc)[0]


def mathml_to_latex_batch(
    formulas: Iterable[str], *, pandoc: str | Path = "pandoc",
) -> list[str | None]:
    results: list[str | None] = []
    fragments: list[str] = []
    positions: dict[str, int] = {}
    for index, mathml in enumerate(formulas):
        results.append(None)
        fragment = _mathml_html(mathml)
        if fragment is not None:
            key = f"mathml-{index}"
            positions[key] = index
            fragments.append(f'<div id="{key}">{fragment}</div>')

    if not fragments:
        return results

    try:
        converted = subprocess.run(
            [str(pandoc), "--from=html", "--to=json"],
            input="\n".join(fragments),
            encoding="utf-8",
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Pandoc не найден: {pandoc}. Укажите путь или добавьте его в PATH.") from error

    for block in json.loads(converted.stdout)["blocks"]:
        if block["t"] != "Div":
            continue
        (key, _, _), contents = block["c"]
        if key in positions:
            inlines = [
                inline
                for item in contents if item["t"] in {"Plain", "Para"}
                for inline in item["c"]
            ]
            if len(inlines) == 1 and inlines[0]["t"] == "Math":
                results[positions[key]] = inlines[0]["c"][1].strip() or None
    return results


def _mathml_html(mathml: str) -> str | None:
    try:
        root = ElementTree.fromstring(mathml)
    except ElementTree.ParseError:
        return None
    if root.tag not in {"math", f"{MATHML_PREFIX}math"}:
        return None

    for element in root.iter():
        element.tag = element.tag.removeprefix(MATHML_PREFIX)
    for semantics in root.iter("semantics"):
        for annotation in semantics.findall("annotation"):
            semantics.remove(annotation)
    root.set("xmlns", MATHML_NS)
    return ElementTree.tostring(root, encoding="unicode", short_empty_elements=False)
