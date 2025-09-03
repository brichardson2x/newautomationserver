<#
.SYNOPSIS
    Copies ALL group memberships (mail-enabled and non-mail-enabled) from one user to another.
.DESCRIPTION
    This wrapper script runs both Exchange Online (mail-enabled) and Graph (non-mail-enabled)
    membership copies in sequence. It includes retry logic:
      - Exchange Online waits up to 30 minutes for the target user to appear.
      - Graph waits up to 6 minutes for the target user to appear.
    Unlike the strict version, this version will continue to Graph even if Exchange fails.
.PARAMETER SourceUser
    UPN (email) of the user to copy memberships from.
.PARAMETER TargetUser
    UPN (email) of the user to copy memberships to.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$SourceUser,

    [Parameter(Mandatory=$true)]
    [string]$TargetUser,

    # Programmatic auth parameters
    [Parameter(Mandatory=$true)]
    [string]$BearerToken,

    [Parameter(Mandatory=$true)]
    [string]$ServiceAccountUser,

    [Parameter(Mandatory=$true)]
    [string]$ServicePass
)

### convert credentials/token once for programmatic execution
$securepass = ConvertTo-SecureString $ServicePass -AsPlainText -Force
$securebearer = ConvertTo-SecureString $BearerToken -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($ServiceAccountUser, $securepass)

### --- Exchange Online Section (Mail-Enabled Groups) ---
Write-Host "`n=== [Step 1] Connecting to Exchange Online ==="
try {
    Connect-ExchangeOnline -Credential $credential -ErrorAction Stop

    # Retry loop for Exchange provisioning
    $maxRetries = 60   # 30 minutes
    $retryDelay = 30
    $found = $false

    for ($i=1; $i -le $maxRetries; $i++) {
        try {
            $null = Get-Recipient -Identity $TargetUser -ErrorAction Stop
            Write-Host "Target user $TargetUser found in Exchange."
            $found = $true
            break
        } catch {
            Write-Warning "Target user $TargetUser not found in Exchange yet. Retrying in $retryDelay seconds... ($i/$maxRetries)"
            Start-Sleep -Seconds $retryDelay
        }
    }

    if ($found) {
        # Get all distribution and mail-enabled security groups
        $distGroups = Get-DistributionGroup -ResultSize Unlimited
        foreach ($group in $distGroups) {
            try {
                # Use Guid as the unique group identifier
                $members = Get-DistributionGroupMember -Identity $group.Guid -ResultSize Unlimited
                if ($members.PrimarySmtpAddress -contains $SourceUser) {
                    try {
                        Add-DistributionGroupMember -Identity $group.Guid -Member $TargetUser -ErrorAction Stop
                        Write-Host "Added $TargetUser to mail-enabled group $($group.DisplayName) <$($group.PrimarySmtpAddress)> (Guid: $($group.Guid))"
                    } catch {
                        Write-Warning "Failed to add $TargetUser to $($group.DisplayName) (Guid: $($group.Guid)): $_"
                    }
                }
            } catch {
                Write-Warning "Could not enumerate members of $($group.DisplayName) (Guid: $($group.Guid)): $_"
            }
        }
    } else {
        Write-Error "Target user $TargetUser not found in Exchange after waiting $($maxRetries * $retryDelay / 60) minutes. Skipping Exchange group copy."
    }
} catch {
    Write-Error "Exchange section failed: $_"
} finally {
    Disconnect-ExchangeOnline -Confirm:$false
}

### --- Graph Section (Non-Mail-Enabled Groups) ---
Write-Host "`n=== [Step 2] Connecting to Microsoft Graph ==="
try {
    # Connect once using the bearer token provided programmatically
    Connect-MgGraph -AccessToken $securebearer -ErrorAction Stop -NoWelcome

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
        Write-Error "Target user $TargetUser not found in Graph after waiting $($maxRetries * $retryDelay / 60) minutes. Skipping Graph group copy."
    } else {
        # Get source user
        $source = Get-MgUser -UserId $SourceUser
        if (-not $source) {
            Write-Error "Source user $SourceUser not found in Graph. Skipping Graph group copy."
        } else {
            # Get all groups of source user (full group objects expanded)
            $rawGroups = Get-MgUserMemberOf -UserId $source.Id | Where-Object { $_.AdditionalProperties.'@odata.type' -eq "#microsoft.graph.group" }
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
                        New-MgGroupMember -GroupId $group.Id -DirectoryObjectId $target.Id -ErrorAction Stop
                        Write-Host "Added $TargetUser to group $($group.displayName)"
                    } catch {
                        Write-Warning "Failed to add $TargetUser to group $($group.DisplayName): $_"
                    }
                }
            } else {
                Write-Host "No non-mail-enabled groups found for $SourceUser."
            }
        }
    }
} catch {
    Write-Error "Graph section failed: $_"
} finally {
    Disconnect-MgGraph | Out-Null
}

Write-Host "`n=== Group copy process completed (Exchange + Graph attempted) ==="