#!/usr/bin/env python3
"""Turn every Rollout in a rendered manifest stream into the Pod it would create, for admission-policy checks.

Kyverno's offline CLI knows Deployments and Jobs but not Argo Rollouts, so without this the most important
workloads would silently skip the policy tests. Reads multi-document YAML on stdin, writes Pods on stdout.
Needs PyYAML (school-gitops/requirements.txt).
"""
import sys

import yaml


def pods(docs):
    for d in docs:
        if not d or d.get("kind") != "Rollout":
            continue
        t = d["spec"]["template"]
        meta = dict(t.get("metadata", {}))
        meta["name"] = d["metadata"]["name"] + "-pod"
        meta["namespace"] = d["metadata"].get("namespace", "default")
        yield {"apiVersion": "v1", "kind": "Pod", "metadata": meta, "spec": t["spec"]}


if __name__ == "__main__":
    out = list(pods(yaml.safe_load_all(sys.stdin)))
    if not out:
        sys.exit("no Rollouts found: the policy checks would test nothing")
    yaml.safe_dump_all(out, sys.stdout, sort_keys=False)
