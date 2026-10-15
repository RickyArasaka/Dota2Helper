@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo           DotaBlitz - Compilar para Executavel (.exe)
echo ========================================================

cd /d "%~dp0\.."

:: 1. Ativar venv se existir, ou usar python do sistema
if exist "venv\Scripts\activate.bat" (
    echo [*] Ativando ambiente virtual venv...
    call venv\Scripts\activate.bat
)

:: 2. Instalar dependencias e PyInstaller
echo [*] Verificando instalacao do PyInstaller e dependencias...
pip install pyinstaller pywebview -r requirements.txt

:: 3. Limpar builds anteriores
echo [*] Limpando pastas de build antigas...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"

:: 4. Compilar usando o arquivo .spec
echo.
echo [*] Iniciando compilacao com PyInstaller...
python -m PyInstaller DotaBlitz.spec --noconfirm

echo.
if exist "dist\DotaBlitz.exe" (
    echo ========================================================
    echo [OK] Executavel gerado com sucesso!
    echo Localizacao: %CD%\dist\DotaBlitz.exe
    echo.
    echo Basta clicar duas vezes em 'dist\DotaBlitz.exe' para usar!
    echo ========================================================
) else (
    echo [ERRO] A geracao do executavel falhou. Verifique as mensagens de erro acima.
)

pause
