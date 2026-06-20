from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

LEAK_KINDS = frozenset({
    "Leak_DefinitelyLost",
    "Leak_IndirectlyLost",
    "Leak_PossiblyLost",
    "Leak_StillReachable",
})

# Kinds that count toward "definite" memory problems (exclude StillReachable)
_DEFINITE_LEAK_KINDS = LEAK_KINDS - {"Leak_StillReachable"}


@dataclass
class ValgrindError:
    kind: str
    description: str
    leaked_bytes: int = 0
    leaked_blocks: int = 0
    file: str | None = None
    line: int | None = None
    function: str | None = None

    @property
    def is_leak(self) -> bool:
        return self.kind in LEAK_KINDS


@dataclass
class ValgrindResult:
    errors: list[ValgrindError] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_leaks(self) -> bool:
        return any(e.is_leak for e in self.errors)

    @property
    def definitely_lost_bytes(self) -> int:
        return sum(e.leaked_bytes for e in self.errors if e.kind == "Leak_DefinitelyLost")

    @property
    def total_leaked_bytes(self) -> int:
        return sum(e.leaked_bytes for e in self.errors if e.kind in _DEFINITE_LEAK_KINDS)


def _first_user_frame(stack_el: ET.Element) -> tuple[str | None, int | None, str | None]:
    """Return (file, line, function) from the first frame that has a <file> tag."""
    for frame in stack_el.findall("frame"):
        file_el = frame.find("file")
        if file_el is not None and file_el.text:
            line_el = frame.find("line")
            fn_el = frame.find("fn")
            line = int(line_el.text) if line_el is not None and line_el.text else None
            fn = fn_el.text if fn_el is not None else None
            return file_el.text, line, fn
    return None, None, None


def parse_valgrind_xml(xml_text: str) -> ValgrindResult:
    """Parse Valgrind --xml=yes output into a ValgrindResult.

    Raises ValueError if the XML is malformed.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"XML de Valgrind inválido: {e}") from e

    errors: list[ValgrindError] = []

    for error_el in root.findall("error"):
        kind_el = error_el.find("kind")
        kind = kind_el.text if kind_el is not None and kind_el.text else "Unknown"

        xwhat = error_el.find("xwhat")
        if xwhat is not None:
            text_el = xwhat.find("text")
            description = text_el.text if text_el is not None and text_el.text else ""
            lb_el = xwhat.find("leakedbytes")
            lk_el = xwhat.find("leakedblocks")
            leaked_bytes = int(lb_el.text) if lb_el is not None and lb_el.text else 0
            leaked_blocks = int(lk_el.text) if lk_el is not None and lk_el.text else 0
        else:
            what_el = error_el.find("what")
            description = what_el.text if what_el is not None and what_el.text else ""
            leaked_bytes = 0
            leaked_blocks = 0

        file, line, function = None, None, None
        stack_el = error_el.find("stack")
        if stack_el is not None:
            file, line, function = _first_user_frame(stack_el)

        errors.append(ValgrindError(
            kind=kind,
            description=description,
            leaked_bytes=leaked_bytes,
            leaked_blocks=leaked_blocks,
            file=file,
            line=line,
            function=function,
        ))

    return ValgrindResult(errors=errors)
