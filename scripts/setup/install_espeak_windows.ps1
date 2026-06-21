# Instala espeak-ng (requerido por phonemizer) en Windows.
$ErrorActionPreference = "Stop"

$msiUrl = "https://github.com/espeak-ng/espeak-ng/releases/download/1.50/espeak-ng-20191129-b702b03-x64.msi"
$msiPath = Join-Path $env:TEMP "espeak-ng-x64.msi"

Write-Host "Descargando espeak-ng..."
Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath

Write-Host "Instalando espeak-ng (puede pedir permisos de administrador)..."
Start-Process msiexec.exe -Wait -ArgumentList "/i `"$msiPath`" /qn"

$dll = "C:\Program Files\eSpeak NG\libespeak-ng.dll"
if (-not (Test-Path $dll)) {
    throw "No se encontro $dll despues de la instalacion."
}

Write-Host "Listo: $dll"
