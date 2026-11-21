# Solar Tracker EDA Dashboard

A Python-only interactive dashboard built with Streamlit, Pandas, NumPy and Plotly.

## Run in VS Code

1. Open this folder in VS Code.
2. Open the terminal in this folder.
3. Create a virtual environment (recommended):

   Windows PowerShell:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

5. Start the dashboard:
   ```powershell
   streamlit run app.py
   ```

6. Open the local URL printed in the terminal (usually http://localhost:8501).

## Use your dataset

Use the sidebar uploader to upload your cleaned CSV. The app recognises the solar tracker
column names such as Temperature_C, Irradiance_Wm2, Voltage_V, Current_A, Power_W,
Energy_Wh, LDR_Top, LDR_Bottom, LDR_Left, LDR_Right, Azimuth_Deg and Elevation_Deg.

If no CSV is uploaded, the dashboard opens a multi-week view with day/night cycles,
changing weather, and natural variation in solar output and sensor readings.

Use the sidebar start/end date and time controls to select any interval. Dates are not
restricted to the timestamps currently in the dataset; choosing an interval with no
matching records displays an empty-range notice. The Reports page provides its own
start/end date and time controls for exports. An uploaded CSV is used when provided.

## Pages

- Overview
- Data Exploration
- Performance Analysis
- Sensor & Tracking
- Data Quality
- Reports and CSV export

The dashboard is for offline analysis and does not connect to Arduino, ESP32, or physical sensors.
