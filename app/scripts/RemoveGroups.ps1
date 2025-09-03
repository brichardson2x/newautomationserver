<#
.SYNOPSIS
    Removes group memberships (mail-enabled and non-mail-enabled) from a target user.
.DESCRIPTION
    Uses Exchange Online and Microsoft Graph to remove a user's memberships. Designed for
    programmatic execution: accepts a bearer token and service account credentials instead
    of interactive sign-in.
.PARAMETER BearerToken
    OAuth2 bearer token for Microsoft Graph (application token).
.PARAMETER ServiceAccountUser
    Service account username used for Exchange Online connection (UPN).
.PARAMETER ServicePass
    Service account password (plain text) used for Exchange Online connection.
.PARAMETER TargetUser
    UPN (email) or display name of the user to remove group memberships from.
.PARAMETER SourceUser
    Optional: UPN or display name of a source/clone user whose groups should be used to limit removals.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$SourceUser,

    [Parameter(Mandatory=$true)]
    [string]$TargetUser,

    [Parameter(Mandatory=$true)]
    [string]$BearerToken,

    [Parameter(Mandatory=$true)]
    [string]$ServiceAccountUser,

    [Parameter(Mandatory=$true)]
    [string]$ServicePass
)

$ErrorActionPreference = "SilentlyContinue"
$requiredModules = @("ExchangeOnlineManagement", "Microsoft.Graph.Users", "Microsoft.Graph.Groups")

foreach ($module in $requiredModules) {
    if (Get-Module -ListAvailable -Name $module) {
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

Write-Host "Converting credentials and preparing connections"
$securepass = ConvertTo-SecureString $ServicePass -AsPlainText -Force
$securebearer = ConvertTo-SecureString $BearerToken -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($ServiceAccountUser, $securepass)

### --- Connect to Exchange Online using service credential ---
Write-Host "Connecting to Exchange Online"
try {
    Connect-ExchangeOnline -Credential $credential -ShowBanner:$false -ErrorAction Stop
    Write-Host "Connected to Exchange Online"
} catch {
    Write-Warning ("Failed to connect to Exchange Online: {0}" -f $_)
}

### --- Connect to Microsoft Graph using supplied bearer token ---
Write-Host "Connecting to Microsoft Graph"
try {
    Connect-MgGraph -AccessToken $securebearer -ErrorAction Stop -NoWelcome
    Write-Host "Connected to Microsoft Graph"
} catch {
    Write-Warning ("Failed to connect to Microsoft Graph: {0}" -f $_)
}

### --- Exchange Online Section (mail-enabled groups removal) ---
Write-Host "`n=== [Step 1] Removing mail-enabled (Exchange) groups ==="
try {
    # Retry loop for Exchange provisioning
    $maxRetries = 60   # 30 minutes
    $retryDelay = 30
    $found = $false

    for ($i=1; $i -le $maxRetries; $i++) {
        try {
            $null = Get-Recipient -Identity $TargetUserAccount -ErrorAction Stop
            Write-Host "Target user $TargetUser found in Exchange."
            $found = $true
            break
        } catch {
            Write-Warning "Target user $TargetUser not found in Exchange yet. Retrying in $retryDelay seconds... ($i/$maxRetries)"
            Start-Sleep -Seconds $retryDelay
        }
    }

    if ($found) {
        # iterate distribution groups and remove target if member
        $distGroups = Get-DistributionGroup -ResultSize Unlimited
        foreach ($group in $distGroups) {
            try {
                $members = Get-DistributionGroupMember -Identity $group.Guid -ResultSize Unlimited
                # attempt to detect membership by recipient id or primary smtp
                $isMember = $false
                try {
                    if ($members.Id -contains $TargetUserAccount) { $isMember = $true }
                } catch {}
                try {
                    if ($members.PrimarySmtpAddress -contains $TargetUser) { $isMember = $true }
                } catch {}

                if ($isMember) {
                    try {
                        Remove-DistributionGroupMember -Identity $group.Guid -Member $TargetUser -Confirm:$false -ErrorAction Stop
                        Write-Host "Removed $TargetUser from mail-enabled group $($group.DisplayName)"
                    } catch {
                        Write-Warning "Failed to remove $TargetUserAccount from $($group.DisplayName): $_"
                    }
                }
            } catch {
                Write-Warning "Could not enumerate members of $($group.DisplayName) (Guid: $($group.Guid)): $_"
            }
        }
    } else {
        Write-Error "Target user $TargetUserAccount not found in Exchange after waiting $($maxRetries * $retryDelay / 60) minutes. Skipping Exchange group removals."
    }
} catch {
    Write-Error "Exchange removal section failed: $_"
} finally {
    try { Disconnect-ExchangeOnline -Confirm:$false } catch {}
}

### --- Graph Section (non-mail-enabled groups) ---
Write-Host "`n=== [Step 2] Removing Graph (non-mail-enabled) group memberships ==="
try {
    # Retry loop for Graph provisioning
    $maxRetries = 12   # 6 minutes
    $retryDelay = 30
    $target = $null

    for ($i=1; $i -le $maxRetries; $i++) {
        try {
            $target = Get-MgUser -UserId $TargetUser -ErrorAction Stop
            Write-Host "Target user $TargetUser found in Graph."
            break
        } catch {
            Write-Warning "Target user $TargetUser not found in Graph yet. Retrying in $retryDelay seconds... ($i/$maxRetries)"
            Start-Sleep -Seconds $retryDelay
        }
    }

    if (-not $target) {
    Write-Error "Target user $TargetUser not found in Graph after waiting. Skipping Graph removals."
    } else {
        # Determine groups to remove: from clone (if provided) or from target's memberships
        if ($SourceUser) {
            if ($SourceUser -match "\s") {
                $source = Get-MgUser -Filter "DisplayName eq '$SourceUser'" | Select-Object -First 1
            } else {
                $source = Get-MgUser -Filter "userPrincipalName eq '$SourceUser'" | Select-Object -First 1
            }
            if (-not $source) {
                Write-Error "Source/clone user $SourceUser not found. Skipping Graph removals."
            } else {
                $rawGroups = Get-MgUserMemberOf -UserId $source.Id | Where-Object { $_.AdditionalProperties.'@odata.type' -eq "#microsoft.graph.group" }
            }
        } else {
            $rawGroups = Get-MgUserMemberOf -UserId $target.Id | Where-Object { $_.AdditionalProperties.'@odata.type' -eq "#microsoft.graph.group" }
        }

        $groups = @()
        foreach ($raw in $rawGroups) {
            try {
                $fullGroup = Get-MgGroup -GroupId $raw.Id -ErrorAction Stop
                if (-not $fullGroup.MailEnabled) {
                    $groups += $fullGroup
                }
            } catch {
                Write-Warning "Failed to expand group $($raw.Id): $_"
            }
        }

        if ($groups) {
            foreach ($group in $groups) {
                try {
                    Remove-MgGroupMember -GroupId $group.Id -DirectoryObjectId $target.Id -ErrorAction Stop
            Write-Host "Removed $TargetUser from group $($group.displayname)"
                } catch {
            Write-Warning "Failed to remove $TargetUser from group $($group.DisplayName): $_"
                }
            }
        } else {
        Write-Host "No non-mail-enabled groups found to remove for $TargetUser."
        }
    }
} catch {
    Write-Error "Graph removal section failed: $_"
} finally {
    try { Disconnect-MgGraph | Out-Null } catch {}
}

Write-Host "`n=== Group removal process completed (Exchange + Graph attempted) ==="
