# Free hosting: Render + private Hugging Face dataset

Hugging Face authentication succeeded for `ritikbhai`. The private dataset `ritikbhai/sat-sahib-library` has the 336-page Gyan Ganga index and original PDF. No public Space was created: Hugging Face returned HTTP 402 and stated that Docker/Gradio CPU hosting requires PRO. We did not subscribe or select paid hardware.

Render's official free-service documentation was checked on 2026-10-12:
https://render.com/docs/free
https://render.com/docs/blueprint-spec

Render currently documents 750 free instance hours per workspace/month. Free services sleep after 15 minutes without traffic; waking can take about a minute. Local file changes can disappear on spin-down/redeploy. This app restores its library from the private HF dataset at startup and backs up after successful admin uploads. Check the free quota in your account before deployment; do not select paid upgrades. Private dataset upload and restore were tested successfully in this cloud environment: 1 book, 336 pages and the original PDF were restored. A restart on the eventual Render host still needs validation.

## Deploy

1. Sign in to Render using your GitHub account and grant access only to `Ritikbhai0/Kabir-Ai`.
2. Once the application code and `render.yaml` are pushed, create a Blueprint from that repository and branch `deploy/free-web-app`. The YAML explicitly sets `plan: free` and provisions no paid disks or databases.
3. Render prompts for `HF_TOKEN`. Enter the actual token in Render's secret field, not in Git or chat. It needs read/write access to the private dataset `ritikbhai/sat-sahib-library`. A Codex proxy placeholder must not be copied into Render.
4. `ADMIN_PASSWORD` is generated automatically by Render. Read it in your own Render Environment settings and keep it private. Use it at `/admin.html`. Normal users have no upload controls or upload permission.
5. After deployment, verify a Hindi question, PDF source, admin upload, successful backup, and restart/restore. Sleep-related first-load delay is expected on the free plan.

The provided deployment has not yet been created on Render: Render account access is required. The existing private PDF backup is preserved. Do not delete or expose its credentials.
