# Canadian Fire Visualization Web App

This folder contains a Streamlit version of the original Jupyter notebook dashboards.
The notebooks in `analysis/` are unchanged.

## Run locally

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r web_app/requirements.txt
streamlit run web_app/app.py
```

The app reads `data/processed/fire_data_sample.csv` and renders both interactive
Altair dashboards in browser tabs.

## Deploy

You can deploy this folder with Streamlit Community Cloud or another Python web
hosting service. Set the app entry point to:

```text
web_app/app.py
```
