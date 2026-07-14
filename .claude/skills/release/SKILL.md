---
name: release
description: Cut a new syhwp release to PyPI — bump the version, tag it, and let the trusted-publishing workflow publish. Use when asked to release or publish a new version.
---

# Release syhwp to PyPI

Publishing is automated by `.github/workflows/publish.yml` (PyPI trusted
publishing / OIDC — no token needed). To cut a release:

1. Make sure `main` is green:

       pytest -q

2. Bump the version in **both** files, keeping them identical:
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `src/syhwp/__init__.py` → `__version__ = "X.Y.Z"`
3. Move the `CHANGELOG.md` "Unreleased" items under a new `## [X.Y.Z]` heading.
4. Commit and push the bump, then create and push the matching tag:

       git commit -am "release: vX.Y.Z"
       git push origin main
       git tag vX.Y.Z
       git push origin vX.Y.Z

5. The tag push triggers the workflow, which builds and publishes to PyPI. Verify:

       pip index versions syhwp     # or check https://pypi.org/project/syhwp/

## Notes / gotchas

- The workflow job must have `permissions: id-token: write` **and**
  `contents: read`. Without `contents: read`, `actions/checkout` fails with
  "repository not found" on a private repo.
- One-time PyPI setup: a Trusted Publisher (pending publisher for the first
  release) pointing at repo `sysphere/syhwp`, workflow `publish.yml`,
  environment `pypi`.
- The PyPI project page shows the README of the *published* version, so a
  docs-only change only appears on PyPI after a new release.
- If a downstream project pins `syhwp==X.Y.Z`, bump that pin too.
