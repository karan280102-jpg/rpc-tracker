# RPC Projection Tracker

Live Farmley dashboard: monthly projection vs quantity sent to RPC warehouses, pendency, fulfilment and rates.

- **Open it:** https://karan280102-jpg.github.io/rpc-tracker/
- **Data:** the Google Sheet "Pendency Data" (tabs: RPC Raw Material, Projection Qty, Non-Usable Data).
  - Each browser reads the sheet when the page opens and when Refresh is clicked.
  - The **Sync Google Sheet** workflow also copies the sheet into `data/` every 10 minutes. If a browser or office network blocks Google, the page reads that copy instead.
- **To update numbers:** edit the Google Sheet. Nothing to upload here.
- **Instant sync:** Actions → Sync Google Sheet → Run workflow.
- **To change the dashboard design:** replace `index.html`.
