# assets/

This folder is intended to hold static assets for the repository (images, icons, social preview images, and other binary/static files).

Suggested files and conventions
- assets/social-preview.png — repository social preview / Open Graph image (recommended size: 1280x640 or 640x320)
- assets/logo.svg — project logo or icon
- assets/screenshots/* — example screenshots used in READMEs or docs

How to add binary files
- Use the web UI "Upload files" button or add/commit locally (see CLI below).
- For large images prefer to optimize or track them in an "assets" subfolder per-feature to keep repo organized.

Example usage
- Link images from README or docs with relative paths, e.g. `![screenshot](assets/screenshots/example.png)`

If you want me to add example images, attach them here or tell me the filenames and I’ll prepare a patch including those binaries.