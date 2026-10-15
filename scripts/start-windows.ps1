# Portable source launch. No registry, PATH or startup modifications.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
& py -3 -B (Join-Path $projectRoot 'bin\run.py') @args desktop
exit $LASTEXITCODE
