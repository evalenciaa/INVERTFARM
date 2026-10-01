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
$LogPath = Join-Path $LogDirectory 'respaldo_programado.log'

Start-Transcript -Path $LogPath -Append | Out-Null
try {
    Set-Location -LiteralPath $ProjectPath
    & $PythonPath 'manage.py' 'crear_respaldo' '--motivo' 'programado'
    if ($LASTEXITCODE -ne 0) {
        throw "El comando de respaldo terminó con código $LASTEXITCODE."
    }
}
finally {
    Stop-Transcript | Out-Null
}
