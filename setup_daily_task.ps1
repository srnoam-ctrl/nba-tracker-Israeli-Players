<#
.SYNOPSIS
    Registers a Windows Scheduled Task to run the NBA & Sport 5 Tracker daily.
#>

$taskName = "NBA_Deni_Avdija_Channel5_Tracker"
$workingDir = "c:\Apps\NBA Channel 5 tracker"
$pythonPath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"

if (-not (Test-Path $pythonPath)) {
    $pythonCmd = (Get-Command python.exe -ErrorAction SilentlyContinue)
    if ($pythonCmd) {
        $pythonPath = $pythonCmd.Source
    } else {
        Write-Error "Python executable not found. Please verify Python installation."
        exit 1
    }
}

$scriptPath = Join-Path $workingDir "run_tracker.py"

Write-Host "Registering daily scheduled task '$taskName'..." -ForegroundColor Cyan
Write-Host "Python Path: $pythonPath"
Write-Host "Script: $scriptPath"

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "run_tracker.py" -WorkingDirectory $workingDir
$trigger = New-ScheduledTaskTrigger -Daily -At "07:00AM"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

try {
    # Unregister existing if present
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Daily sync for Deni Avdija NBA games and Israeli TV broadcast schedule (Sport 5)"
    Write-Host "Successfully registered Windows Task '$taskName' to run daily at 07:00 AM IST!" -ForegroundColor Green
} catch {
    Write-Warning "Could not register task automatically. If running without Admin rights, you can run PowerShell as Administrator or execute tracker.bat on demand."
    Write-Error $_
}
