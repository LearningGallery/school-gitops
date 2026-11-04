# school-gitops

Desired state for the School Management System. **Argo CD watches this repository; CI never touches the cluster.**

```text
apps/root.yaml                  the one object applied by hand: app of apps
argocd/                         AppProject, ApplicationSet (dev, staging), platform Applications
base/                           every Kubernetes object once (Deployments, Services, Ingress, ExternalSecret, migration + smoke Jobs)
overlays/{dev,staging}/   what differs: namespace, replicas, host, flags, secret names, image digests
platform/external-secrets/      ClusterSecretStore (no credentials: EKS Pod Identity)
policies/kyverno/               admission policies (CEL) with unit tests
scripts/                        validate.sh (offline checks), set_image.py (the only promotion edit)
```

## Check everything offline

```bash
make gitops-check        # from the repository root; needs kubectl and docker, no cluster, no AWS
```

Renders each overlay, validates it against Kubernetes and CRD schemas (`kubeconform`), runs the Kyverno policy tests, and applies the policies to every rendered environment.

## Promotion

`school-app/.github/workflows/promote.yml` verifies provenance for two digests and opens a pull request that changes only the `digest:` lines of one overlay. Merging makes it the desired state. See [module 14](../docs/14-gitops-fundamentals/README.md).

## Before first use

Replace `<YOUR_ORG>` in `apps/root.yaml`, `argocd/*.yaml` and `policies/kyverno/rules/school-verify-attestations.yaml`, and the placeholder account ID, certificate ARN, database host and RDS secret names in the overlays. Nothing here has been applied to a cluster.
