# HackNation 2026

Team project for HackNation 2026 in Bydgoszcz (21-22 Nov 2026).

**Team:** Marco Gnudi, Wiktor

## The challenge
_To be filled in once the challenge is announced._

## How we work
- `main` must always be demo-ready.
- Work on a short-lived branch: `feat/<thing>`, `fix/<thing>`.
- Commit small and often with clear messages.
- Merge into `main` via a small pull request; pull `main` often.

```bash
git checkout main && git pull
git checkout -b feat/my-feature
# ...work...
git add -A && git commit -m "Add my feature"
git push -u origin feat/my-feature
gh pr create --fill
```

## Running locally

`start_ui.bat` starts one server from `back-end2` on http://127.0.0.1:8000 and the page on http://127.0.0.1:8080. Regular mode is Wiktor's deterministic extractor. Bielik mode keeps those values and fills empty fields from `backend/`. `./back-end2/start.sh` starts the same server.

## Deploying

The `Dockerfile` builds one container that serves the page and the API, with Tesseract and its Polish data installed, so visitors install nothing.

```bash
docker build -t przetargo .
docker run -p 8000:8000 przetargo
```

Then open http://127.0.0.1:8000/.

To put it online on Render: in the dashboard, choose **New > Blueprint** and pick this repository. Render reads `render.yaml`, builds the `Dockerfile`, and deploys again on every push to `main`. The blueprint uses the paid Starter plan; free instances sleep after 15 idle minutes and take about a minute to wake, which judges would notice.

The image sets `PRZETARGO_HOSTED=1`. On a hosted site:

- Each visitor enters their own Bielik key (a Hugging Face token) in the page. The browser keeps it in session storage, or local storage if they tick "remember", and sends it as the `X-LLM-Key` header. The server does not log or store it.
- If `LLM_API_KEY` is set on the server, it is used when a visitor leaves the field empty. Leave it unset unless you want to pay for every visitor's calls.
- Uploads are processed in temporary files and returned as JSON. Nothing is written to `input/`, `output/` or the Bielik and OCR caches, and the input folder controls are hidden.
- The page offers the task's example cases (text PDFs and scans) so visitors can try it without their own documents.
