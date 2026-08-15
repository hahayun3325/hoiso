from pathlib import Path
import subprocess
import sys
import time
import requests
from bs4 import BeautifulSoup

OUT_DIR = Path("/home/fredcui/datasets/hoi/dexycb/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PAGE = "https://dex-ycb.github.io/"

# Minimal for Phase 0.17 mini-panel.
MINIMAL_NAMES = [
    "20200709-subject-01.tar.gz",
    "calibration.tar.gz",
    "models.tar.gz",
]

# Full official subject-wise dataset.
FULL_NAMES = [
    "20200709-subject-01.tar.gz",
    "20200813-subject-02.tar.gz",
    "20200820-subject-03.tar.gz",
    "20200903-subject-04.tar.gz",
    "20200908-subject-05.tar.gz",
    "20200918-subject-06.tar.gz",
    "20200928-subject-07.tar.gz",
    "20201002-subject-08.tar.gz",
    "20201015-subject-09.tar.gz",
    "20201022-subject-10.tar.gz",
    "bop.tar.gz",
    "calibration.tar.gz",
    "models.tar.gz",
]

mode = sys.argv[1] if len(sys.argv) > 1 else "minimal"
wanted = MINIMAL_NAMES if mode == "minimal" else FULL_NAMES

html = requests.get(PAGE, timeout=30).text
soup = BeautifulSoup(html, "html.parser")

links = {}
for a in soup.find_all("a"):
    text = a.get_text(strip=True)
    href = a.get("href")
    if text in wanted and href:
        links[text] = href

missing = [x for x in wanted if x not in links]
if missing:
    raise SystemExit(f"[ERROR] Could not find links for: {missing}")

print("[INFO] mode:", mode)
print("[INFO] output:", OUT_DIR)
for name in wanted:
    print("[INFO]", name, links[name])

for name in wanted:
    out = OUT_DIR / name
    if out.exists() and out.stat().st_size > 1024 * 1024:
        print(f"[SKIP] exists: {out}")
        continue

    cmd = [
        "gdown",
        "--continue",
        links[name],
        "-O",
        str(out),
    ]

    print("\n===== downloading", name, "=====")
    print(" ".join(cmd))

    ok = False
    for attempt in range(1, 4):
        print(f"[INFO] attempt {attempt}/3")
        ret = subprocess.run(cmd)
        if ret.returncode == 0 and out.exists() and out.stat().st_size > 1024 * 1024:
            ok = True
            break
        print("[WARN] failed; sleeping 5 minutes before retry")
        time.sleep(300)

    if not ok:
        print(f"[ERROR] failed to download {name}; continuing to next file")
