# Brandon Richardson 3/7/24 based on Max's original
param (
    [string]$BearerToken,
    [string]$ServiceAccountUser,
    [string]$ServicePass,
    [string]$TargetUserAccount,
    [string]$CloneUserAccount
)


$requiredModules = @("ExchangeOnlineManagement", "Microsoft.Graph.Users", "Microsoft.Graph.Groups")

foreach ($module in $requiredModules) {
    if (Get-Module -ListAvailable -Name $module) {
        Write-Host "Module $module is installed"
        try {
            Import-Module -Name $module -ErrorAction Stop
            Write-Host "Module $module loaded successfully"
        } catch {
            Write-Host "ERROR: Failed to import module $module. Error: $_"
        }
    } else {
        Write-Host "ERROR: Required module $module is not installed on this system"
    }
}

Write-Host "Convert Credentials to Secure String"
$securepass = ConvertTo-SecureString $ServicePass -AsPlainText -Force
$securebearer = ConvertTo-SecureString $BearerToken -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($ServiceAccountUser, $securepass)


Write-Host "Connecting to Exchange Online and Graph API"
Write-Host "Connecting to Exchange Online"
try {
    Connect-ExchangeOnline -Credential $credential
    Write-Host "Successfully connected to Exchange Online"
} catch {
    Write-Host "ERROR: Failed to connect to Exchange Online. Error: $_"
}

Write-Host "Connecting to Microsoft Graph"
try {
    Connect-MgGraph -AccessToken $securebearer
    Write-Host "Successfully connected to Microsoft Graph"
} catch {
    Write-Host "ERROR: Failed to connect to Microsoft Graph. Error: $_"
}

Write-Host "Getting Groups from Clone User"

if ($CloneUserAccount -match "\s") {
    $CloneId = Get-MgUser -Filter "DisplayName eq '$CloneUserAccount'" | Select-Object -First 1
    $ClonedGroups = Get-MgUserMemberof -UserId $CloneId.Id  # add group ids to variable
} else {
    $CloneId = Get-MgUser -Filter "userPrincipalName eq '$CloneUserAccount'"
    $ClonedGroups = Get-MgUserMemberof -UserId $CloneId.Id  # add group ids to variable
}

Write-Host "Splitting groups into Graph and Exchange"
Write-Host "$CloneId"

$GraphGroups = @()
$ExchangeGroups = @()

$ClonedGroups | ForEach-Object {
$group = Get-MgGroup -GroupId $_.IdUpdateE
    if ($group.GroupTypes -eq "Unified") {
        $GraphGroups += $group.Id
    } elseif ($group.MailEnabled) {
        $ExchangeGroups += $group.Id
    } else {
        $GraphGroups += $group.Id
    }
}

Write-Host "$ExchangeGroups"
Write-Host "$GraphGroups"

Write-Host "Checking if Target User passed is display name or UPN"
if ($TargetUserAccount -match "\s") {
    Write-Host "Getting User by Display Name"
    $TargetId = Get-MgUser -Filter "DisplayName eq '$TargetUserAccount'"
    Write-Host "Getting User UPN and DN"
    $TargetUPN = $TargetId.UserPrincipalName
    $TargetDN = $TargetId.Id
    Write-Host "Adding Graph Groups to User"
    $GraphGroups | ForEach-Object {New-MgGroupMemberByRef -ErrorAction SilentlyContinue -GroupId $_ -OdataId "https://graph.microsoft.com/v1.0/users/$TargetUPN"}    # add groups to user with graph api
    $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    while ($null -eq $holdon) {
        Start-Sleep -Seconds 1
        $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    }
    Write-Host "Adding Exchange Groups to User"
    $ExchangeGroups | ForEach-Object {Add-DistributionGroupMember -ErrorAction SilentlyContinue -BypassSecurityGroupManagerCheck -Identity $_ -Member $TargetDN}  # add groups to user with exchange module
} else {
    Write-Host "Getting User by UPN"
    $TargetId = Get-MgUser -Filter "userPrincipalName eq '$TargetUserAccount'"
    Write-Host "Getting User UPN and DN"
    $TargetUPN = $TargetId.UserPrincipalName
    $TargetDN = $TargetId.Id
    $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    while ($null -eq $holdon) {
        Start-Sleep -Seconds 1
        $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    }
    Write-Host "Adding Graph Groups to User"
    $GraphGroups | ForEach-Object {New-MgGroupMemberByRef -ErrorAction SilentlyContinue -GroupId $_ -OdataId "https://graph.microsoft.com/v1.0/users/$TargetUPN"}    # add groups to user with graph api
    Write-Host "Adding Exchange Groups to User"
    $ExchangeGroups | ForEach-Object {Add-DistributionGroupMember -ErrorAction SilentlyContinue -BypassSecurityGroupManagerCheck -Identity $_ -Member $TargetDN}   # add groups to user with exchange module
}

Write-Host "Check if Default User Login Policy Group exists"
$DefaultPolicyGroup = "697ec5bf-f312-4ef2-ad34-bf830cc7d00a"
$DefaultUserLoginPolicyExist = $ClonedGroups | Where-Object {$_.Id -eq $DefaultPolicyGroup}


if ($null -eq $DefaultUserLoginPolicyExist) {
    New-MgGroupMemberByRef -ErrorAction SilentlyContinue -GroupId $DefaultPolicyGroup -OdataId "https://graph.microsoft.com/v1.0/users/$TargetUPN"
}




