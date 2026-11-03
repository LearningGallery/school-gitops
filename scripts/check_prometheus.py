#!/usr/bin/env python3
"""Check the alert rules and the AnalysisTemplate queries with promtool, using synthetic traffic.

1. PrometheusRule -> plain rules file -> `promtool check rules` and `promtool test rules` (alerts_test.yaml)
2. AnalysisTemplate queries (arguments filled with sample values) -> recording rules -> check and test (analysis_test.yaml)

No Prometheus server and no cluster. Needs docker (pinned promtool image) and PyYAML.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROMTOOL = "prom/prometheus@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2"  # v3.15.1
SAMPLE_ARGS = {"namespace": "school-staging", "canary-hash": "canary1"}
NAMES = {"error-ratio": "analysis:error_ratio", "latency-p95-seconds": "analysis:latency_p95_seconds", "enrollment-failures": "analysis:enrollment_failures"}


def promtool(work, *args):
    # Run as the caller: the temp dir is private (0700), and the image's default user could not read it on Linux runners.
    cmd = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}", "--entrypoint", "promtool", "-v", f"{work}:/work:ro", PROMTOOL, *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    return r.returncode


def main():
    rule = yaml.safe_load((ROOT / "platform/monitoring/prometheusrule.yaml").read_text())
    template = yaml.safe_load((ROOT / "base/analysis.yaml").read_text())
    analysis = []
    for m in template["spec"]["metrics"]:
        q = m["provider"]["prometheus"]["query"]
        for k, v in SAMPLE_ARGS.items():
            q = q.replace("{{args.%s}}" % k, v)
        if "{{" in q:
            sys.exit(f"unfilled argument in {m['name']}: {q}")
        analysis.append({"record": NAMES[m["name"]], "expr": " ".join(q.split())})
    with tempfile.TemporaryDirectory() as t:
        work = Path(t)
        (work / "school-rules.yaml").write_text(yaml.safe_dump({"groups": rule["spec"]["groups"]}))
        (work / "analysis-rules.yaml").write_text(yaml.safe_dump({"groups": [{"name": "analysis", "rules": analysis}]}))
        for f in ("alerts_test.yaml", "analysis_test.yaml"):
            (work / f).write_text((ROOT / "platform/monitoring/tests" / f).read_text())
        rc = 0
        for rules in ("school-rules.yaml", "analysis-rules.yaml"):
            rc |= promtool(work, "check", "rules", f"/work/{rules}")
        for tests in ("alerts_test.yaml", "analysis_test.yaml"):
            rc |= promtool(work, "test", "rules", f"/work/{tests}")
    # the dashboard must at least be valid JSON with queries in it
    import json
    d = json.loads((ROOT / "platform/monitoring/dashboard.json").read_text())
    assert len([p for p in d["panels"] if p.get("targets")]) >= 6, "dashboard lost its panels"
    return rc


if __name__ == "__main__":
    sys.exit(main())
