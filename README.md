# DIFY-SANDBOX-PY

[English](README.md) | [中文](README_CN.md)

A code executor for Dify that is compatible with the official sandbox API calls and dependency installation.

- Supports Python 3.14
- Supports Node.js 20
- Includes API contract tests for Dify 1.16.1

## Purpose

The official sandbox provides stronger isolation through strict permission and syscall controls. This project is intended for trusted, self-authored Dify code nodes that need broader permissions and dependencies such as NumPy, Matplotlib, and scikit-learn.

## Usage

Build the Python 3.14 image:

```shell
docker build -t dify-sandbox-py:python3.14 .
```

Replace the sandbox image in Dify's `docker-compose.yaml`:

```yaml
sandbox:
  # image: langgenius/dify-sandbox:0.2.15
  image: dify-sandbox-py:python3.14
```

## Screenshots

Python support
![](/images/Xnip2024-11-25_11-30-12.jpg)

Node.js support
![](/images/Xnip2024-11-25_11-31-01.jpg)

Docker container logs
![](/images/Xnip2025-04-28_16-48-48.jpg)

## Notes

- Network access restrictions have been removed; network access is enabled by default.
- UV installs dependencies from `/dependencies/python-requirements.txt` when the container starts.
- The image only contains API runtime dependencies. Add application libraries to `python-requirements.txt` and pin their versions.
- Configure a package index with `PIP_MIRROR_URL` when needed.
- Python code that exceeds `WORKER_TIMEOUT` terminates and replaces the affected process pool.
- This executor favors compatibility over isolation and must only run trusted code.
