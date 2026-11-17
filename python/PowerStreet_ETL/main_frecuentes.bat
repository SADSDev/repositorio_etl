@echo off

cd /d "%~dp0"
set "PYTHONPATH=%~dp0..;%PYTHONPATH%"

for /d %%D in (*venv*) do (
    call "%%D\Scripts\activate.bat"
    goto :venv_activado
)

:venv_activado
python diario/diarios_frecuentes/main.py

exit
