# Packaged artifacts

The repository keeps its full unpacked source on `main`.

GitHub Actions builds these deployment archives from the current source tree:

- `openclaw-stock-analyst-pi.zip`
- `openclaw-stock-analyst-pi.tar.gz`
- `SHA256SUMS`

The packaging workflow also writes the generated archives back into this directory after a normal `main` push, so they can be downloaded directly from the repository.
