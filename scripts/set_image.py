#!/usr/bin/env python3
"""Write new image digests into overlays/<env>/kustomization.yaml (the only edit a promotion makes).

usage: set_image.py <env> --backend sha256:... --frontend sha256:...
"""
import argparse
import re
import sys
from pathlib import Path

DIGEST = re.compile(r"^sha256:[a-f0-9]{64}$")


def set_digest(text, image, digest):
    pattern = re.compile(rf"(- name: {re.escape(image)}\n(?:    newName: .*\n)?    digest: )sha256:[a-f0-9]{{64}}")
    new, n = pattern.subn(rf"\g<1>{digest}", text)
    if n != 1:
        raise SystemExit(f"expected exactly one images entry for {image}, found {n}")
    return new


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("env", choices=["dev", "staging", "production"])
    ap.add_argument("--backend", required=True)
    ap.add_argument("--frontend", required=True)
    ap.add_argument("--root", default=Path(__file__).resolve().parent.parent, type=Path)
    a = ap.parse_args(argv)
    for d in (a.backend, a.frontend):
        if not DIGEST.match(d):
            raise SystemExit(f"not a sha256 digest: {d!r}")  # never write a tag or a typo into Git
    path = a.root / "overlays" / a.env / "kustomization.yaml"
    text = set_digest(set_digest(path.read_text(), "school-backend", a.backend), "school-frontend", a.frontend)
    path.write_text(text)
    print(f"{a.env}: backend={a.backend[:19]}... frontend={a.frontend[:19]}...")


if __name__ == "__main__":
    sys.exit(main())
