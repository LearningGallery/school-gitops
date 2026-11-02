#!/usr/bin/env bash
# Offline checks for school-gitops: render every overlay, validate against Kubernetes and CRD schemas,
# run the Kyverno policy tests, and prove each rendered environment passes the policies.
# Needs: kubectl (for `kubectl kustomize`) and docker. No cluster, no AWS.
set -euo pipefail
cd "$(dirname "$0")/.."

KUBECONFORM=ghcr.io/yannh/kubeconform@sha256:faffaf43f95aa6425306e1ab8d6fcad72acb9049158f38e574c085ea1ec0f64e # v0.8.0
KYVERNO=ghcr.io/kyverno/kyverno-cli@sha256:322ec5044d600930cb3af0e56dc33154a2d1d1fba58f4cadad3f47be7e78b11c   # v1.19.2, matches the Kyverno chart
CRD_CATALOG=27233a506de0085e71c7f9702597806a7f95eb24 # datreeio/CRDs-catalog commit: schemas for Argo CD and External Secrets
K8S_VERSION=1.33.0                                    # keep in step with the EKS version in school-infra
SCHEMAS=(-schema-location default -schema-location "https://raw.githubusercontent.com/datreeio/CRDs-catalog/${CRD_CATALOG}/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json")

conform() { docker run --rm -i "$KUBECONFORM" -strict -summary -kubernetes-version "$K8S_VERSION" "${SCHEMAS[@]}" -ignore-missing-schemas -; }

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

for env in dev staging production; do
  echo "== overlay: $env"
  kubectl kustomize "overlays/$env" > "$tmp/$env.yaml"
  conform < "$tmp/$env.yaml"
done

for dir in argocd platform/external-secrets policies/kyverno; do
  echo "== $dir"
  kubectl kustomize "$dir" | conform
done

echo "== kyverno: policy tests (good and bad fixtures)"
docker run --rm -v "$PWD/policies/kyverno:/p:ro" "$KYVERNO" test /p/tests

echo "== kyverno: rendered environments against the policies"
for env in dev staging production; do
  docker run --rm -v "$PWD/policies/kyverno/rules:/rules:ro" -v "$tmp/$env.yaml:/r.yaml:ro" "$KYVERNO" apply \
    /rules/school-restrict-images.yaml /rules/school-pod-security.yaml /rules/school-resources-and-labels.yaml --resource /r.yaml \
    | tee "$tmp/kyverno-$env.txt" | tail -1
  grep -q "fail: 0" "$tmp/kyverno-$env.txt" || { echo "policy failures in $env"; exit 1; }
done

echo "== promotion script"
python3 scripts/test_set_image.py
echo "gitops-check: ok"
