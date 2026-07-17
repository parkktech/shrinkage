# CI

`tests.yml` is the GitHub Actions workflow for the repo's pytest suite. It
lives here (not in `.github/workflows/`) because pushing workflow files
requires a PAT with the Workflows permission. To activate it:

    mkdir -p .github/workflows && cp ci/tests.yml .github/workflows/

and push from a client with workflow scope — or paste it via the GitHub web
editor (Add file → Create new file → `.github/workflows/tests.yml`).
