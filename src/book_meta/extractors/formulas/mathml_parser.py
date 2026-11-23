import re
from typing import Optional

def extract_latex_from_mathml(block_raw: dict) -> Optional[str]:
    """
    Извлекает готовый LaTeX из MathML.
    Если MathML нет или в нем нет аннотации — возвращает None.
    """
    mathml = block_raw.get("mathml")
    if not mathml:
        return None

    match = re.search(r'<annotation[^>]*encoding="[^"]*tex[^"]*"[^>]*>(.*?)</annotation>', mathml, re.DOTALL)
    
    if match:
        return match.group(1).strip()
        
    return None
