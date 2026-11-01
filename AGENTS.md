# Agent notes

`vodafone-station-cli` is a Python command-line client for a Vodafone Station.

- Preserve the CLI behavior documented in `README.md`.
- Run the repository's Python lint workflow and add focused tests for behavior
  changes. Use a test device or mock for integration checks.
- The `main` push workflow builds a container image. Do not change its
  publication settings without an explicit request.
- Before changing workflows, check for reusable workflows or actions in
  [ci-workflows](https://github.com/pschmitt/ci-workflows) and preserve
  existing triggers, parameters, and check coverage.
