@echo off
echo Activating Conda environment: RealityEditorPipeline

:: Activate the Conda environment
call conda activate RealityEditorPipeline

if errorlevel 1 (
    echo Error: Conda environment activation failed.
    exit /b 1
)

:: Run script1.py
echo Running script1.py
python script1.py

:: Run script2.py
echo Running script2.py
python script2.py

:: Deactivate the Conda environment (optional)
echo Deactivating Conda environment
call conda deactivate

:: Pause to see the output (optional)
pause