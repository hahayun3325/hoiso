from pathlib import Path
import argparse
import json
import shutil

HOME = Path.home()

SRC_ROOT = (HOME / "foho_phase0/runs/oakink000_gpt55_short").resolve()
MANIFEST = HOME / "foho_phase0/inspection/arctic_phase017/salvage_manifest_all_arctic_from_oakink000_gpt55_short.json"

CASE_IDS = [
    "abox01",
    "aket01",
    "ascis01",
    "alapuse01",
    "amicuse01",
]

PROTECTED_TOKENS = [
    "oakink",
]

def is_under(path: Path, root: Path) -> bool:
    path = path.resolve()
    root = root.resolve()
    return path == root or root in path.parents

def looks_like_arctic_case_path(path: Path) -> bool:
    rel = str(path.resolve().relative_to(SRC_ROOT))
    return any(case_id in rel for case_id in CASE_IDS)

def verify_file_pair(src: Path, dst: Path):
    if not src.exists():
        return False, "source_missing"
    if not dst.exists():
        return False, "destination_missing"
    if not src.is_file() or not dst.is_file():
        return False, "not_file_pair"
    if src.stat().st_size != dst.stat().st_size:
        return False, f"size_mismatch src={src.stat().st_size} dst={dst.stat().st_size}"
    return True, "ok"

def verify_dir_pair(src: Path, dst: Path):
    if not src.exists():
        return False, "source_missing"
    if not dst.exists():
        return False, "destination_missing"
    if not src.is_dir() or not dst.is_dir():
        return False, "not_dir_pair"

    src_files = sorted([p for p in src.rglob("*") if p.is_file()])
    if not src_files:
        return True, "ok_empty_dir"

    for sf in src_files:
        rel = sf.relative_to(src)
        df = dst / rel
        if not df.exists():
            return False, f"missing_copied_file {df}"
        if sf.stat().st_size != df.stat().st_size:
            return False, f"size_mismatch {sf} -> {df}"
    return True, "ok"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually delete files/directories")
    args = ap.parse_args()

    if not MANIFEST.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST}")

    entries = json.loads(MANIFEST.read_text())
    print("SRC_ROOT:", SRC_ROOT)
    print("MANIFEST:", MANIFEST)
    print("MODE:", "APPLY_DELETE" if args.apply else "DRY_RUN_ONLY")
    print("entries:", len(entries))

    deleted = []
    skipped = []

    # Delete deeper directories first, then files.
    entries = sorted(entries, key=lambda x: len(str(x.get("src", ""))), reverse=True)

    for e in entries:
        src = Path(e["src"]).resolve()
        dst = Path(e["dst"]).resolve()
        typ = e.get("type", "")

        if not is_under(src, SRC_ROOT):
            skipped.append((src, "not_under_src_root"))
            continue

        if not looks_like_arctic_case_path(src):
            skipped.append((src, "does_not_look_like_arctic_case_file"))
            continue

        if any(tok in src.name.lower() and not looks_like_arctic_case_path(src) for tok in PROTECTED_TOKENS):
            skipped.append((src, "protected_token"))
            continue

        if typ == "file":
            ok, reason = verify_file_pair(src, dst)
            if not ok:
                skipped.append((src, reason))
                continue

            print("[DELETE FILE]" if args.apply else "[DRY FILE]", src)
            if args.apply:
                src.unlink()
            deleted.append(str(src))

        elif typ == "dir":
            ok, reason = verify_dir_pair(src, dst)
            if not ok:
                skipped.append((src, reason))
                continue

            print("[DELETE DIR]" if args.apply else "[DRY DIR]", src)
            if args.apply:
                shutil.rmtree(src)
            deleted.append(str(src))

        else:
            skipped.append((src, f"unknown_type={typ}"))

    print("\n===== summary =====")
    print("deleted_or_would_delete:", len(deleted))
    print("skipped:", len(skipped))

    if skipped:
        print("\n===== skipped details =====")
        for p, reason in skipped:
            print("[SKIP]", reason, p)

    out = HOME / "foho_phase0/inspection/arctic_phase017/delete_salvaged_arctic_from_oakink_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "mode=" + ("apply" if args.apply else "dry_run") + "\n"
        + "deleted_or_would_delete=\n"
        + "\n".join(deleted)
        + "\n\nskipped=\n"
        + "\n".join(f"{reason}: {p}" for p, reason in skipped)
    )
    print("\n[OK] wrote", out)

if __name__ == "__main__":
    main()
