Connect-MgGraph -BearerToken $BearerToken

$devices = Get-MgDeviceManagementManagedDevice -All

$currentDate = Get-Date
$pastDate = $currentDate.AddDays(-30)

$windowsDevices = $devices | Where-Object { $_.operatingSystem -eq "Windows" }
$stuckDevices = $windowsDevices | Where-Object { $_.LastSyncDateTime -lt $pastDate }
$leftover = $stuckDevices.Count

return $leftover