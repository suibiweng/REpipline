@echo off
REM === Activate the Conda environment "TexTURE" ===
call "C:\Users\cuiro\anaconda3\condabin\activate.bat" TexTURE


REM === Launch the servers in new command windows with proper working directories ===

REM Server 1: RealityEditng20.py (in the current directory)
start cmd /k "python RealityEditing20.py"

REM Server 2: TextureChangeServer.py (one level up in TEXTurePaper folder)
start cmd /k "cd /d ..\TEXTurePaper && python TextureChangeServer.py"

REM Server 3: Real3DServer.py (one level up in Real3D folder)
start cmd /k "cd /d ..\Real3D && python Real3DServer.py"

REM Server 4: ShapEserver.py (in the current directory)
start cmd /k "python ShapEserver.py"

REM === Launch the separate .bat file (run.bat) in the sd.webui folder (one level up) ===
start cmd /k "cd /d ..\sd.webui && conda deactivate & call run.bat"

pause
