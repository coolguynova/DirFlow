# install.ps1 - Automated startup installer for Local File Organizer on Windows

$scriptDir = $PSScriptRoot
$pythonBin = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonBin) {
    $pythonBin = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
}
if (-not $pythonBin) {
    Write-Error "Python was not found in your system PATH. Please install Python first."
    Exit 1
}

# Use pythonw (windowless Python) so it runs silently in the background
$pythonwBin = $pythonBin.Replace("python.exe", "pythonw.exe")
if (Test-Path $pythonwBin) {
    $execBin = $pythonwBin
} else {
    $execBin = $pythonBin
}

$startupFolder = [System.Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "LocalFileOrganizer.lnk"

echo "Installing Local File Organizer to Windows Startup..."

# Create shortcut using WScript.Shell COM object
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $execBin
$Shortcut.Arguments = """$scriptDir\organizer.py"""
$Shortcut.WorkingDirectory = $scriptDir
$Shortcut.Description = "Lightweight Local File Organizer Daemon"
$Shortcut.Save()

# Stop any running instances first
Stop-Process -Name "pythonw" -ErrorAction SilentlyContinue
Stop-Process -Name "python" -ErrorAction SilentlyContinue -Filter "CommandLine like '*organizer.py*'"

# Launch the daemon now in background
Start-Process -FilePath $execBin -ArgumentList """$scriptDir\organizer.py""" -WorkingDirectory $scriptDir

Write-Host ""
Write-Host "=========================================================="
Write-Host "✔ Installation successful!"
Write-Host "✔ Shortcut created in Windows Startup folder: $shortcutPath"
Write-Host "✔ Daemon started running silently in the background!"
Write-Host "=========================================================="
Write-Host "To stop the daemon, close it via Task Manager or run:"
Write-Host "  Stop-Process -Name 'pythonw'"
Write-Host ""
