# Releasing mpbuild

Cutting a release is two steps: merge a version-bump PR, then push a tag. Everything else (build, PyPI upload, GitHub release) happens automatically via `.github/workflows/release.yml`.

## TL;DR

```bash
# 1. Open + merge a "Release vX.Y.Z" PR that bumps:
#    - pyproject.toml (project.version)
#    - src/mpbuild/__init__.py (__version__)
#    - uv.lock (uv lock)
#
# 2. Tag the merged commit on main and push:
git checkout main
git pull --ff-only
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

The tag push triggers the release workflow. Done.

## What a release produces

| Artefact | Where |
|---|---|
| New version | https://pypi.org/project/mpbuild/ |
| Git tag `vX.Y.Z` | https://github.com/mattytrentini/mpbuild/tags |
| GitHub release with auto-generated notes + wheel/sdist | https://github.com/mattytrentini/mpbuild/releases |

## Step-by-step

### 1. Decide the version

[SemVer](https://semver.org/):

- **Patch** (`1.0.X`) — bug fixes only.
- **Minor** (`1.X.0`) — backwards-compatible new behaviour.
- **Major** (`X.0.0`) — breaking change to the CLI.

The CLI is the stable surface that SemVer applies to. The Python module API (`import mpbuild`) is documented as a work in progress; treat changes there as out of band.

### 2. Open a release PR

Bump these three files in a single PR titled "Release vX.Y.Z":

- `pyproject.toml` — `project.version = "X.Y.Z"`
- `src/mpbuild/__init__.py` — `__version__ = "X.Y.Z"` (this is what `mpbuild --version` actually prints)
- `uv.lock` — run `uv lock` after the bump to keep it in sync

If anything user-visible changed since the last release (new commands, key bindings, behaviour, etc.), update `README.md` in the same PR.

Branch protection requires CI to pass: `test`, `lint`, and `typecheck` all run automatically. The PR's CI must be green before merge.

### 3. Tag the merged commit and push

```bash
git checkout main
git pull --ff-only        # picks up the merged release PR
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

Annotated tags (`-a -m`) record the tagger and a tag message, which downstream tooling (e.g. release notes, `git describe`) prefers over lightweight tags.

### 4. Watch the workflow

```bash
gh run watch
# or browse https://github.com/mattytrentini/mpbuild/actions
```

Three sequential jobs:

1. **`build`** — `uv build` creates the wheel + sdist and uploads them as a workflow artefact.
2. **`publish-pypi`** — uploads to PyPI via OIDC trusted publishing.
3. **`github-release`** — creates the GitHub release with `--generate-notes`, attaching the wheel + sdist as assets.

If the `pypi` GitHub Environment has "Required reviewers" enabled, `publish-pypi` waits for an approval click — that's the chance to download the artefact from the `build` job and sanity-check it before it hits PyPI.

### 5. Verify

After the workflow goes green (~1 minute for PyPI to index, in addition to the workflow time):

```bash
uv tool install --python 3.12 --force mpbuild==X.Y.Z
mpbuild --version            # expect: mpbuild vX.Y.Z
```

Then eyeball the GitHub release page at `https://github.com/mattytrentini/mpbuild/releases/tag/vX.Y.Z` — auto-generated notes can be edited via the UI if you want a "Highlights" section above the PR list.

## One-off setup (already done; here for reference)

PyPI trusted publishing must be configured at https://pypi.org/manage/project/mpbuild/settings/publishing/ with:

- **Owner**: `mattytrentini`
- **Repository name**: `mpbuild`
- **Workflow name**: `release.yml`
- **Environment name**: `pypi`

This is what makes "publish without a long-lived PyPI token" work: PyPI trusts the GitHub Actions OIDC identity for that exact workflow file in that exact repo's `pypi` environment. If any of those four fields don't match between PyPI and the workflow, the upload step fails with an OIDC token error.

## Troubleshooting

**`publish-pypi` fails with "OIDC token" / "trusted publishing" error.**
The PyPI trusted-publisher record doesn't match the workflow. Re-check the four fields under "One-off setup" above — the workflow filename and environment name are the usual culprits.

**`publish-pypi` fails with "filename already exists" / "version already exists".**
PyPI doesn't allow overwriting a version. Bump to the next patch (e.g., if `1.0.1` already exists, release `1.0.2`). You can *yank* a broken release on PyPI (`pip` won't install yanked versions unless explicitly pinned) but you can't re-upload the same version number.

**Tag points at the wrong commit.**
If the workflow hasn't run yet (or hasn't reached `publish-pypi`):

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
# Then re-tag from the correct SHA and push.
```

If `publish-pypi` already succeeded, the PyPI upload is final — see "yank" above and bump to the next patch.

**You need to undo a release after it shipped.**
- *PyPI*: yank the version (Manage → Releases → Options → Yank). Don't delete — that breaks reproducibility of anyone who pinned it.
- *GitHub release*: delete or convert to a pre-release via the UI.
- *Git tag*: leave it in place. Tags should be immutable once published; deleting them confuses anyone who fetched the repo while the tag existed.

## Why tag-driven?

The tag is the source of truth for what got released. Alternatives (e.g. triggering on PR merge, on a release-please bot) couple "I want to merge a PR" with "I want to publish" — which doesn't always line up. Pushing the tag is an explicit "release this now" gesture and lets the release PR sit on main for a while if you want to bundle several merges into one release.
