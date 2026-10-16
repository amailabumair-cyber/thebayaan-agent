# Setup Windows Auto-Start for Agent AM
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "AgentAM.lnk"
$targetScript = "d:\work space\agent\start_agent_hidden.vbs"
$workDir = "d:\work space\agent"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$targetScript`""
$shortcut.WorkingDirectory = $workDir
$shortcut.Description = "Agent AM - The Bayaan YouTube Manager Background Service"
$shortcut.Save()

Write-Host "=========================================================="
Write-Host "ماشاء اللہ! ونڈوز آٹو اسٹارٹ شارٹ کٹ کامیابی سے تیار ہو گیا ہے:"
Write-Host $shortcutPath
Write-Host "=========================================================="
