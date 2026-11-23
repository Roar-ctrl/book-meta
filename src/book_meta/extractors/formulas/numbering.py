import re
from typing import Tuple, Optional

def extract_tag_from_latex(latex: str) -> Tuple[str, Optional[str]]:
    """
    Ищет \\tag{...} в строке LaTeX.
    Возвращает кортеж: (LaTeX_без_тега, номер_или_None)
    """
    match = re.search(r'\\tag\{([^}]+)\}', latex)
    if match:
        number = match.group(1).strip()
        # Удаляем тег из строки
        latex_clean = re.sub(r'\\tag\{[^}]+\}', '', latex).strip()
        return latex_clean, number
    
    return latex, None
