$desktop = [Environment]::GetFolderPath('Desktop')
$ws = New-Object -ComObject WScript.Shell
$path = Join-Path $desktop 'AcidCode.lnk'
$lnk = $ws.CreateShortcut($path)
$lnk.TargetPath = 'C:\Windows\System32\cmd.exe'
$lnk.Arguments = '/c "cd /d C:\Users\Asus\AcidCode && acidcode.cmd"'
$lnk.WorkingDirectory = 'C:\Users\Asus\AcidCode'
$lnk.IconLocation = 'C:\Windows\System32\cmd.exe,0'
$lnk.Description = 'AcidCode'
$lnk.Save()
Write-Output ("shortcut: " + (Test-Path $path))
Write-Output ("path_has_venv: " + (($env:Path -split ';') -contains 'C:\Users\Asus\AcidCode\.venv\Scripts'))
