[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath,

    [Parameter(Mandatory = $true)]
    [string]$PythonPath,

    [string]$TaskName = 'INVENTFARM - respaldo diario',

    [datetime]$At = '02:00',

    [pscredential]$Credential
)

$ErrorActionPreference = 'Stop'
if (-not $Credential) {
    $Credential = Get-Credential -Message 'Cuenta de servicio para los respaldos de INVENTFARM'
}

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$RunnerPath = Join-Path $ProjectPath 'scripts\ejecutar_respaldo_programado.ps1'
if (-not (Test-Path -LiteralPath $RunnerPath -PathType Leaf)) {
    throw "No se encontró el ejecutor programado: $RunnerPath"
}

$PowerShellPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$RunnerPath`" -ProjectPath `"$ProjectPath`" -PythonPath `"$PythonPath`""
$Action = New-ScheduledTaskAction -Execute $PowerShellPath -Argument $Arguments
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -User $Credential.UserName -Password $Credential.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null

Write-Host "Tarea '$TaskName' instalada. Ejecútala una vez desde Task Scheduler y verifica el archivo logs\respaldo_programado.log."
