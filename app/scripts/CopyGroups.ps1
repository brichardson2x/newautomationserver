# Brandon Richardson 3/7/24 based on Max's original
param (
    [string]$BearerToken,
    [string]$ServiceAccountUser,
    [string]$ServicePass,
    [string]$TargetUserAccount,
    [string]$CloneUserAccount
)

$securepass = ConvertTo-SecureString $ServicePass -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($ServiceAccountUser, $securepass)

Connect-ExchangeOnline -Credential $credential
Connect-MgGraph -BearerToken $BearerToken

# Test if email or Name
if ($CloneUserAccount -match "\s") {
    $CloneId = Get-MgUser -Filter "DisplayName eq '$CloneUserAccount'" | Select-Object -First 1
    $ClonedGroups = Get-MgUserMemberof -UserId $CloneId.Id  # add group ids to variable
} else {
    $CloneId = Get-MgUser -Filter "userPrincipalName eq '$CloneUserAccount'"
    $ClonedGroups = Get-MgUserMemberof -UserId $CloneId.Id  # add group ids to variable
}

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


# Check if Useraccounts given in upn or Display Name
if ($TargetUserAccount -match "\s") {   #check for space
    $TargetId = Get-MgUser -Filter "DisplayName eq '$TargetUserAccount'"
    $TargetUPN = $TargetId.UserPrincipalName
    $TargetDN = $TargetId.Id
    $GraphGroups | ForEach-Object {New-MgGroupMemberByRef -ErrorAction SilentlyContinue -GroupId $_ -OdataId "https://graph.microsoft.com/v1.0/users/$TargetUPN"}    # add groups to user with graph api
    $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    while ($null -eq $holdon) {
        Start-Sleep -Seconds 1
        $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    }
    $ExchangeGroups | ForEach-Object {Add-DistributionGroupMember -ErrorAction SilentlyContinue -BypassSecurityGroupManagerCheck -Identity $_ -Member $TargetDN}  # add groups to user with exchange module
} else {
    $TargetId = Get-MgUser -Filter "userPrincipalName eq '$TargetUserAccount'"
    $TargetUPN = $TargetId.UserPrincipalName
    $TargetDN = $TargetId.Id
    $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    while ($null -eq $holdon) {
        Start-Sleep -Seconds 1
        $holdon = Get-Recipient -Identity $TargetDN -ErrorAction SilentlyContinue
    }
    $GraphGroups | ForEach-Object {New-MgGroupMemberByRef -ErrorAction SilentlyContinue -GroupId $_ -OdataId "https://graph.microsoft.com/v1.0/users/$TargetUPN"}    # add groups to user with graph api
    $ExchangeGroups | ForEach-Object {Add-DistributionGroupMember -ErrorAction SilentlyContinue -BypassSecurityGroupManagerCheck -Identity $_ -Member $TargetDN}   # add groups to user with exchange module
}

# Check if already have Default User Login Policy Group
$DefaultPolicyGroup = "697ec5bf-f312-4ef2-ad34-bf830cc7d00a"
$DefaultUserLoginPolicyExist = $ClonedGroups | Where-Object {$_.Id -eq $DefaultPolicyGroup}


if ($null -eq $DefaultUserLoginPolicyExist) {
    New-MgGroupMemberByRef -ErrorAction SilentlyContinue -GroupId $DefaultPolicyGroup -OdataId "https://graph.microsoft.com/v1.0/users/$TargetUPN"
}




