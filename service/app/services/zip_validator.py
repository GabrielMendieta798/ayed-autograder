import zipfile
import subprocess
import shutil
import os

ALLOWED_EXTENSIONS = {".c", ".h", ".cbp", ".mk"}
ALLOWED_FILENAMES = {"makefile"}
MAX_UNCOMPRESSED_MB = 20
MAX_FILES = 50
_CHUNK = 65536
_MAX_BYTES = MAX_UNCOMPRESSED_MB * 1024 * 1024


def validate_and_extract(archive_path: str, dest_dir: str) -> list[str]:
    if archive_path.lower().endswith(".rar"):
        return _extract_rar(archive_path, dest_dir)
    try:
        with zipfile.ZipFile(archive_path, "r") as af:
            return _process_zip(af, dest_dir)
    except zipfile.BadZipFile:
        raise ValueError("El archivo ZIP está corrupto o es inválido")


def _process_zip(zf: zipfile.ZipFile, dest_dir: str) -> list[str]:
    members = zf.infolist()

    if len(members) > MAX_FILES:
        raise ValueError(f"El archivo tiene demasiados archivos ({len(members)})")

    safe_members = []
    for member in members:
        filename = member.filename
        if ".." in filename or filename.startswith("/"):
            raise ValueError(f"Archivo sospechoso detectado: {filename}")
        ext = os.path.splitext(filename)[1].lower()
        basename = os.path.basename(filename).lower()
        if ext in ALLOWED_EXTENSIONS or basename in ALLOWED_FILENAMES:
            safe_members.append(member)

    total_bytes = 0
    for member in safe_members:
        if member.is_dir():
            continue
        out_path = os.path.join(dest_dir, member.filename)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with zf.open(member) as src, open(out_path, "wb") as dst:
            while True:
                chunk = src.read(_CHUNK)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > _MAX_BYTES:
                    raise ValueError(
                        f"El archivo supera el tamaño máximo permitido ({MAX_UNCOMPRESSED_MB}MB descomprimido)"
                    )
                dst.write(chunk)

    return _collect_source_files(dest_dir)


def _extract_rar(rar_path: str, dest_dir: str) -> list[str]:
    # Validate file list before extracting
    list_result = subprocess.run(
        ["tar", "-tf", rar_path],
        capture_output=True, text=True, timeout=30
    )
    if list_result.returncode != 0:
        raise ValueError("El archivo RAR está corrupto o no se puede leer")

    filenames = [
        line.strip() for line in list_result.stdout.splitlines()
        if line.strip() and not line.strip().endswith("/")
    ]

    if len(filenames) > MAX_FILES:
        raise ValueError(f"El archivo tiene demasiados archivos ({len(filenames)})")

    for f in filenames:
        if ".." in f or f.startswith("/"):
            raise ValueError(f"Archivo sospechoso detectado: {f}")

    # Extract to a raw temp dir, then copy only allowed files
    raw_dir = dest_dir + "_raw"
    os.makedirs(raw_dir)
    try:
        extract_result = subprocess.run(
            ["tar", "-xf", rar_path, "-C", raw_dir],
            capture_output=True, text=True, timeout=60
        )
        if extract_result.returncode != 0:
            raise ValueError("No se pudo extraer el archivo RAR")

        total_bytes = 0
        for root, _, files in os.walk(raw_dir):
            for fname in files:
                src = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext not in ALLOWED_EXTENSIONS and fname.lower() not in ALLOWED_FILENAMES:
                    continue
                size = os.path.getsize(src)
                total_bytes += size
                if total_bytes > _MAX_BYTES:
                    raise ValueError(
                        f"El archivo supera el tamaño máximo permitido ({MAX_UNCOMPRESSED_MB}MB descomprimido)"
                    )
                rel = os.path.relpath(src, raw_dir)
                dst = os.path.join(dest_dir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
    finally:
        shutil.rmtree(raw_dir, ignore_errors=True)

    return _collect_source_files(dest_dir)


def _collect_source_files(directory: str) -> list[str]:
    source_files = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith((".c", ".h")):
                source_files.append(os.path.join(root, f))
    return source_files
