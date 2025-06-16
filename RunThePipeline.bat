@echo off

REM === Activate the Conda environment "TexTURE" ===
call "C:\Users\cuiro\anaconda3\condabin\activate.bat" TexTURE

REM === Initial launch of all servers ===
echo Starting all Flask servers initially...

REM Server 1: RealityEditing20.py (in the current directory)
start "RealityEditing20" cmd /k "python RealityEditing20.py"

REM Server 2: TextureChangeServer.py (one level up in TEXTurePaper folder)
start "TextureChangeServer" cmd /k "cd /d ..\TEXTurePaper && python TextureChangeServer.py"

REM Server 3: Real3DServer.py (one level up in Real3D folder)
start "Real3DServer" cmd /k "cd /d ..\Real3D && python Real3DServer.py"

REM Server 4: ShapEserver.py (in the current directory)
start "ShapEserver" cmd /k "python ShapEserver.py"

REM === Launch the separate .bat file (run.bat) in the sd.webui folder (one level up) ===
start "sd.webui" cmd /k "cd /d ..\sd.webui && conda deactivate & call run.bat"

:main
cls
echo Flask Server Control:
echo ----------------------
echo [R] Restart all servers
echo [Q] Quit and close all servers
echo.
set /p choice="Enter your choice: "

if /I "%choice%"=="R" goto restart
if /I "%choice%"=="Q" goto quit
goto main

:restart
echo Restarting Flask servers...
taskkill /F /IM python.exe /T
taskkill /F /FI "WINDOWTITLE eq RealityEditing20*" /T
taskkill /F /FI "WINDOWTITLE eq TextureChangeServer*" /T
taskkill /F /FI "WINDOWTITLE eq Real3DServer*" /T
taskkill /F /FI "WINDOWTITLE eq ShapEserver*" /T
taskkill /F /FI "WINDOWTITLE eq sd.webui*" /T

REM Server 1: RealityEditing20.py (in the current directory)
start "RealityEditing20" cmd /k "python RealityEditing20.py"

REM Server 2: TextureChangeServer.py (one level up in TEXTurePaper folder)
start "TextureChangeServer" cmd /k "cd /d ..\TEXTurePaper && python TextureChangeServer.py"

REM Server 3: Real3DServer.py (one level up in Real3D folder)
start "Real3DServer" cmd /k "cd /d ..\Real3D && python Real3DServer.py"

REM Server 4: ShapEserver.py (in the current directory)
start "ShapEserver" cmd /k "python ShapEserver.py"

REM === Launch the separate .bat file (run.bat) in the sd.webui folder (one level up) ===
start "sd.webui" cmd /k "cd /d ..\sd.webui && conda deactivate & call run.bat"

echo Servers restarted.
pause
goto main

:quit
echo Closing Flask servers and exiting...
taskkill /F /IM python.exe /T
taskkill /F /FI "WINDOWTITLE eq RealityEditing20*" /T
taskkill /F /FI "WINDOWTITLE eq TextureChangeServer*" /T
taskkill /F /FI "WINDOWTITLE eq Real3DServer*" /T
taskkill /F /FI "WINDOWTITLE eq ShapEserver*" /T
taskkill /F /FI "WINDOWTITLE eq sd.webui*" /T

REM Close all cmd windows explicitly
taskkill /F /IM cmd.exe /T

exit
