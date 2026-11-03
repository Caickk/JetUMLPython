@echo off
REM Gera dist\JetUML.exe (um único arquivo, sem console). Requer Python 3.10+ com Tkinter (instalador padrão do Windows).
py -m pip install --upgrade pyinstaller pillow || goto :error
py -m PyInstaller --noconfirm --clean --windowed --onefile --name JetUML run_jetuml.py || goto :error
echo.
echo Pronto: dist\JetUML.exe
goto :eof
:error
echo Falhou. Veja a mensagem acima.
exit /b 1
