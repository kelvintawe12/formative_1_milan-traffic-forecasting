# scripts/dev — exploratory / debug helpers

These files were used while figuring out how to download the Telecom Italia
Milan release through the Harvard Dataverse "guestbook" gate. They are not
part of the main pipeline and are not invoked by `run_everything.{ps1,sh}`.

Kept for reference in case the Dataverse download path needs to be
re-debugged on a different machine or after an API change.

- `diagnose_dataverse.py` — prints what the Dataverse API returns for the
  dataset's file list, useful when the automated downloader fails.
- `GUESTBOOK_SOLUTION.py`, `test_final_guestbook.py`,
  `test_guestbook_methods.py` — three iterations of working around the
  anonymous-download block (final answer: use an authenticated API token
  via the `DATAVERSE_API_TOKEN` env var).
- `test_html_extraction.py`, `test_requests_method.py` — earlier
  scraping/probe scripts.

For the actual download flow used in this submission, see
`../01_download_data.{ps1,sh}` and `../_download_dataverse.py`.
