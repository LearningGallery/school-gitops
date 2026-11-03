#!/usr/bin/env python3
"""Self-check for set_image.py: updates exactly the two digests, rejects tags, touches nothing else."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = "sha256:" + "0" * 64
B, F = "sha256:" + "a" * 64, "sha256:" + "b" * 64


def run(root, *args):
    return subprocess.run([sys.executable, str(HERE / "set_image.py"), "--root", str(root), *args], capture_output=True, text=True)


with tempfile.TemporaryDirectory() as t:
    root = Path(t)
    (root / "overlays/dev").mkdir(parents=True)
    # The overlay holds real digests after the first promotion. Normalise them to placeholders so this test checks
    # the script, not whichever release happens to be deployed.
    src = re.sub(r"digest: sha256:[0-9a-f]{64}", f"digest: {OLD}", (HERE.parent / "overlays/dev/kustomization.yaml").read_text())
    k = root / "overlays/dev/kustomization.yaml"
    k.write_text(src)

    r = run(root, "dev", "--backend", B, "--frontend", F)
    assert r.returncode == 0, r.stderr
    out = k.read_text()
    assert out.count(B) == 1 and out.count(F) == 1 and out.count(OLD) == 0
    assert out.replace(B, OLD).replace(F, OLD) == src, "only the two digests may change"

    before = k.read_text()
    r = run(root, "dev", "--backend", "v1.2.3", "--frontend", F)
    assert r.returncode != 0 and "not a sha256 digest" in r.stderr
    assert k.read_text() == before, "a rejected promotion must not modify the file"
print("set_image: ok")
