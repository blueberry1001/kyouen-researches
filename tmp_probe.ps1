Set-Location 'D:\ghq\github.com\yuubinnkyoku\kyouen-researches\night-research'
Get-ChildItem *.exe | Select-Object Name, Length
Write-Output '--- try maxsafe_enum ---'
& '.\maxsafe_enum.exe' 2>&1 | Select-Object -First 30
