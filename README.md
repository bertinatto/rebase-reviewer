# rebase-reviewer

An experimental tool to help with reviewing OpenShift Kubernetes rebase PRs.

## What this does

When OpenShift rebases to a new Kubernetes release, someone needs to manually review commits to ensure:

- UPSTREAM PRs already in the K8s tag are absent from the rebase branch
- UPSTREAM PRs not in the K8s tag are carried forward with equivalent diffs
- UPSTREAM `<carry>` commits are preserved with matching functionality

This tool attempts to automate parts of this review process using Google Gemini AI for semantic diff comparison. It's experimental and may have false positives/negatives.

## Prerequisites

- Python 3.8+
- Git
- Environment Variables:
  - `GEMINI_API_KEY`
  - `GITHUB_TOKEN`

## Demo

[![Demo](https://asciinema.org/a/7XF1FJKNNK4piXO70RFKCKNkG.svg)](https://asciinema.org/a/7XF1FJKNNK4piXO70RFKCKNkG)

## Usage

```bash
python main.py
```

The tool will prompt you for:
- Target branch (e.g., `ocp/master`)
- Target starting commit
- Source branch (e.g., `rebase-1.34`)
- Source starting commit
- Kubernetes tag (e.g., `v1.34.1`)

## Example Output

```
Checking commit 1cf2294: UPSTREAM: 74956: apiserver: switch authorization to use protobuf client
  -> Found UPSTREAM PR reference: PR #74956. Checking if present in tag v1.34.1...
  -> PR #74956 is NOT in tag v1.34.1. Checking if it's a locally carried commit...
  -> Found in both branches. Analyzing diffs with Gemini...
  -> ✅ VERIFIED: Diffs are semantically equivalent

Checking commit 4669334: UPSTREAM: <carry>: filter out CustomResourceQuota paths from OpenAPI
  -> Found in both branches. Analyzing diffs with Gemini...
  -> ✅ VERIFIED: Diffs are semantically equivalent

Checking commit 037ad1a: UPSTREAM: <carry>: Extend NodeLogQuery feature
  -> Found in both branches. Analyzing diffs with Gemini...
  -> ❌ FAILURE: Diff mismatch: Both diffs introduce the same set of new features but Diff 1 includes an additional security fix not present in Diff 2

Checking commit d0b5a9c: UPSTREAM: <drop>: hack/update-vendor.sh
  -> SKIPPED (drop commit)

--- Final Review Summary ---

92 Verified Commits:
  - UPSTREAM: 74956: apiserver: switch authorization to use protobuf client
  - UPSTREAM: <carry>: filter out CustomResourceQuota paths from OpenAPI
  - UPSTREAM: <carry>: patch aggregator to allow delegating resources
  ...

30 Failures:
  - UPSTREAM: <carry>: Extend NodeLogQuery feature: Diff mismatch: security fix missing
  - UPSTREAM: <carry>: Remove ValidateHostExternalCertificate from route admission: Not found in rebase-1.34
  ...

11 Skipped Commits:
  - UPSTREAM: <drop>: hack/update-vendor.sh
  - UPSTREAM: <drop>: make update
  ...

28 Notices:
  - fix(kubelet): acquire imageRecordsLock when removing image: Non-standard commit found
  - Clean backoff record earlier: Non-standard commit found
  ...

--- Review Complete ---
```
