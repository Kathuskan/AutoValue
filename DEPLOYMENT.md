# Deploy AutoValue on Render Free

The website, API and saved Extra Trees pipeline run as one web service. No database or training job is needed. `models/selected_model.joblib` must remain tracked in Git.

1. Push `render.yaml`, `requirements-deploy.txt` and the current app/model to your GitHub repository.
2. Sign in at https://dashboard.render.com using GitHub.
3. Choose **New → Blueprint** and connect your AutoValue repository and intended branch.
4. Review the service: `autovalue-lk`, **Free**, Python, one worker, `/health` health check. Do not select a paid plan or paid workspace.
5. Apply the Blueprint and wait for the build and deployment to finish.
6. Open the public URL shown by Render. Check the page styling, select the example vehicle, and submit a prediction. `/health` should return `status: ok` and `model: Extra trees`.

If creating a Web Service manually, use:

| Setting | Value |
| --- | --- |
| Language | Python 3 |
| Root directory | Leave blank |
| Build command | `pip install -r requirements-deploy.txt` |
| Start command | `uvicorn backend.api:app --host 0.0.0.0 --port $PORT --workers 1` |
| Instance type | Free |
| Health check | `/health` |
| Environment | `PYTHON_VERSION=3.11.11`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` |

The model's scikit-learn and numerical-library versions are pinned. Python 3.11 is used for hosting; confirm model startup and the example prediction in the Linux deployment before sharing the URL. Training is never run during deployment. The existing local launcher remains available for local use.

Free services sleep after 15 minutes of inactivity and can take about a minute to wake. Free resource and monthly usage limits apply. If the service runs out of memory, inspect Render logs; do not upgrade to a paid plan without deciding to do so. See https://render.com/docs/free.

After deployment, visitors use the public HTTPS URL even when your laptop is off. Stop public access by suspending the service in Render; stopping the local terminal does not stop the hosted service.
