import re
from typing import Tuple, Optional

def extract_tag_from_latex(latex: str) -> Tuple[str, Optional[str]]:
    """Возвращает LaTeX без тега и сам номер."""
    match = re.search(r'\\tag\*?\s*\{([^{}]+)\}', latex)
    if match:
        number = match.group(1).strip()
        latex_clean = re.sub(r'\\tag\*?\s*\{[^{}]+\}', '', latex).strip()
        return latex_clean, number
    return latex, None
