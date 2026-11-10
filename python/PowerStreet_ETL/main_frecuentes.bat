@echo off

cd /d "%~dp0"

for /d %%D in (*venv*) do (
    call "%%D\Scripts\activate.bat"
    goto :venv_activado
)

:venv_activado
python diario/diarios_frecuentes/main.py

pause