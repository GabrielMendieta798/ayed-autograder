import re
from app.models.models import CheckEstatico


def run_static_checks(source_files: list[str], checks: list[CheckEstatico]) -> list[dict]:
    source_code = ""
    for path in source_files:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source_code += f.read() + "\n"

    results = []
    for check in checks:
        matches = re.findall(check.pattern, source_code)

        if check.check_type == "exists":
            passed = len(matches) > 0
        elif check.check_type == "count_gte":
            passed = len(matches) >= check.min_count
        else:
            passed = False

        results.append({
            "descripcion": check.descripcion,
            "passed": passed,
            "found": len(matches),
        })

    return results
