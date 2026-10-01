[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath,

    [Parameter(Mandatory = $true)]
    [string]$PythonPath,

    [string]$TaskName = 'INVENTFARM - procesador de respaldos',

    [pscredential]$Credential
)

$ErrorActionPreference = 'Stop'
if (-not $Credential) {
    $Credential = Get-Credential -Message 'Cuenta de servicio para procesar los respaldos de INVENTFARM'
}

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$RunnerPath = Join-Path $ProjectPath 'scripts\ejecutar_cola_respaldos.ps1'
if (-not (Test-Path -LiteralPath $RunnerPath -PathType Leaf)) {
    throw "No se encontró el procesador: $RunnerPath"
}

$PowerShellPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$RunnerPath`" -ProjectPath `"$ProjectPath`" -PythonPath `"$PythonPath`""
$Action = New-ScheduledTaskAction -Execute $PowerShellPath -Argument $Arguments
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -User $Credential.UserName -Password $Credential.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null

Write-Host "Tarea '$TaskName' instalada. Procesará una solicitud pendiente por minuto; las instancias simultáneas se omiten."
