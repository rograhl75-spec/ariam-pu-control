@echo off
cd /d "%~dp0"
python -m streamlit run app_tablet.py --server.port 8502
pause