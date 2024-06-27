import dataclasses
import pathlib
import subprocess
from typing import Optional


@dataclasses.dataclass
class LatexResult:
    result: subprocess.CompletedProcess[bytes]
    pdf: Optional[bytes]


class Latex:
    def __init__(self, latex: str):
        self.latex = latex

    def build_pdf(self, temp_dir: pathlib.Path) -> LatexResult:
        temp_path = temp_dir / 'statement.tex'
        output_path = temp_path.with_suffix('.pdf')
        args = ['pdflatex', '-interaction', 'nonstopmode', str(temp_path)]
        temp_path.write_text(self.latex)

        completed = subprocess.run(args, timeout=15, capture_output=True, cwd=temp_dir)
        if completed.returncode != 0 or not output_path.exists():
            return LatexResult(result=completed, pdf=None)

        return LatexResult(result=completed, pdf=output_path.read_bytes())
