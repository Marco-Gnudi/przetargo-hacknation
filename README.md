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

`start_ui.bat` starts the app at http://localhost:8000. Regular mode is Wiktor's deterministic extractor. Bielik mode keeps those values and fills empty fields from `backend/`. `./back-end2/start.sh` starts the same server.

`python scripts/make_f1_chart.py` reads `reports/stats.json` from `backend/scripts/evaluate.py` and writes `reports/charts/f1_overview.png`.
