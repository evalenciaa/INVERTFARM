[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath,

    [Parameter(Mandatory = $true)]
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$LogDirectory = Join-Path $ProjectPath 'logs'
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$LogPath = Join-Path $LogDirectory 'cola_respaldos.log'

Start-Transcript -Path $LogPath -Append | Out-Null
try {
    Set-Location -LiteralPath $ProjectPath
    & $PythonPath 'manage.py' 'procesar_trabajos_respaldo'
    if ($LASTEXITCODE -ne 0) {
        throw "El procesador de respaldos terminó con código $LASTEXITCODE."
    }
}
finally {
    Stop-Transcript | Out-Null
}
