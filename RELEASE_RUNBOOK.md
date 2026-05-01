# Release Runbook — v0.2.0 and beyond

This is a one-time-per-release manual checklist. The automation handles everything except the items marked **HUMAN**.

## Pre-release: one-time PyPI setup (HUMAN)

Before the first release ever, configure PyPI trusted publishing:

1. Go to https://pypi.org and create the project name `call-cleaner` (or claim it if it doesn't exist yet).
2. Project settings → Publishing → Add trusted publisher → GitHub:
   - Owner: `trehansalil`
   - Repository: `call-cleaner`
   - Workflow name: `release.yml`
   - Environment: `pypi`
3. In GitHub: Settings → Environments → New environment named `pypi` (no extra secrets needed; OIDC handles auth).

You only do this once. Subsequent releases are fully automated.

## Cutting a release

Run from a clean checkout of `main`:

```sh
make release VERSION=0.2.0
```

This will:
- Update `pyproject.toml` and `__init__.py` to the new version.
- Create commit `release: v0.2.0`.
- Create annotated tag `v0.2.0`.
- Push to origin.

GitHub Actions then:
- Builds sdist + wheel.
- Publishes to PyPI via trusted publishing.

Verify within 5 minutes at: https://pypi.org/project/call-cleaner/

## Post-release: Termux-packages PR (HUMAN)

Once v0.2.0 is on PyPI:

1. **Compute the sdist sha256:**
   ```sh
   curl -sL https://files.pythonhosted.org/packages/source/c/call-cleaner/call-cleaner-0.2.0.tar.gz | sha256sum
   ```
2. Fork github.com/termux/termux-packages.
3. Copy `termux-packages-recipe/build.sh` from this repo into your fork at `packages/call-cleaner/build.sh`.
4. Replace `__FILL_IN_AFTER_PYPI_PUBLISH__` with the sha256 from step 1.
5. Open a PR titled `new package: call-cleaner` against `termux/termux-packages`.
   - After the PR is merged, users get `cleaner` directly via `pkg install call-cleaner`. They still need to run `cleaner install-schedule` once to register the daily background job.
6. Track review with `gh pr view` from this repo. Address feedback within 7 days.

## Definition of done

- [ ] Tag `v0.2.0` pushed.
- [ ] PyPI shows `call-cleaner-0.2.0`.
- [ ] `pip install call-cleaner` works in a clean Termux session.
- [ ] Termux-packages PR is open AND first round of review feedback has been addressed.

## Versioning conventions

- Patch (0.2.x) — bug fixes, no behaviour changes.
- Minor (0.x.0) — new features, backward-compatible.
- Major (x.0.0) — breaking config or trash-format changes.
