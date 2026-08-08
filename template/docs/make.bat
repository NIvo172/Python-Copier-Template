@ECHO OFF
SETLOCAL

PUSHD "%~dp0"

IF "%PYTHON%" == "" (
    SET "PYTHON=python"
)

IF "%~1" == "" (
    SET "TARGET=help"
) ELSE (
    SET "TARGET=%~1"
)

IF /I "%TARGET%" == "help" GOTO :help
IF /I "%TARGET%" == "clean" GOTO :build
IF /I "%TARGET%" == "all" GOTO :build
IF /I "%TARGET%" == "html" GOTO :build
IF /I "%TARGET%" == "coverage" GOTO :build

ECHO Unknown documentation target: %TARGET%
SET "STATUS=2"
GOTO :finish

:help
ECHO Documentation targets:
ECHO   all       Build HTML and validate API documentation coverage
ECHO   html      Build HTML documentation
ECHO   coverage  Build and validate API documentation coverage
ECHO   clean     Remove generated documentation files
SET "STATUS=0"
GOTO :finish

:build
%PYTHON% ..\scripts\build_docs.py %TARGET%
SET "STATUS=%ERRORLEVEL%"
GOTO :finish

:finish
POPD
ENDLOCAL & EXIT /B %STATUS%
