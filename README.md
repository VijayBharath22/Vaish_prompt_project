# BillWise MVP

A locally runnable electricity bill analysis demo. It includes a responsive dashboard, six labeled sample months, reviewed bill uploads, deterministic month comparisons, anomaly context, a local assistant, and an illustrative prompt evaluation page.

## Run locally

```bash
npm start
```

Open http://127.0.0.1:5000.

Uploaded documents are stored in `uploads/`; bill metadata is in `bills.json`. The upload flow saves a file and user-confirmed values. OCR and Gemini are not wired in this MVP; missing extraction is never guessed. `.env.example` documents the future Gemini key configuration. The evaluation page explicitly labels its values as illustrative, not model experiments.
# Vaish_prompt_project
