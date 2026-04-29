# Fast Upload

FastAPI server for workers that upload compressed result folders.

## Endpoints

- `GET /health`
- `POST /upload`

`/upload` expects `multipart/form-data`:

- `target_dir`: relative folder under `uploads/`
- `file`: `.zip`, `.tar.gz`, or `.tgz`
- `allow_overwrite`: optional boolean, default `false`

Archive `results.zip` uploaded with `target_dir=experiment_1` extracts into:

`uploads/experiment_1/results/`

## Run

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## Example Upload

```bash
uv run python scripts/upload.py results --target-dir folder
```

Create `.tar.gz` instead:

```bash
uv run python scripts/upload.py results --target-dir folder --format tar.gz
```
