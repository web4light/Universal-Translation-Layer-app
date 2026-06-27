@echo off
echo ============================================================
echo    INSTALACE ADA/ALIRE PRO VAKUOVOU MINCOVNU
echo ============================================================
echo.

REM Vytvor adresar pro Ada toolchain
set ADA_HOME=C:\AdaDev2024
echo [1/5] Vytvarim adresar: %ADA_HOME%
if not exist "%ADA_HOME%" mkdir "%ADA_HOME%"

REM Rozbal ZIP
echo [2/5] Rozbaluji AdaDev2024.zip...
powershell -Command "Expand-Archive -Path 'C:\Users\pan_jeskyne\Downloads\AdaDev2024.zip' -DestinationPath '%ADA_HOME%' -Force"

if %ERRORLEVEL% NEQ 0 (
    echo [CHYBA] Nelze rozbalit ZIP soubor!
    pause
    exit /b 1
)

echo [3/5] Ada toolchain rozbalen do: %ADA_HOME%
echo.

REM Pridej do PATH (aktualni session)
set PATH=%ADA_HOME%\Alire\bin;%PATH%

echo [4/5] Testuji instalaci...
echo.

REM Test Alire
alr --version
if %ERRORLEVEL% NEQ 0 (
    echo [CHYBA] Alire neni dostupny!
    pause
    exit /b 1
)

echo.
echo [5/5] HOTOVO!
echo ============================================================
echo    ADA/ALIRE USPESNE NAINSTALOVANO
echo ============================================================
echo.
echo Alire je dostupny v: %ADA_HOME%\Alire\bin\alr.exe
echo.
echo DULEZITE: Pridej do systemoveho PATH:
echo    %ADA_HOME%\Alire\bin
echo.
echo Pro pridani do PATH spust:
echo    setx PATH "%%PATH%%;%ADA_HOME%\Alire\bin"
echo.
pause
