param (
    [string]$ServiceAccountUser,
    [string]$ServicePass,
    [string]$UserAccount
)

$ErrorActionPreference = "SilentlyContinue"
$requiredModules = @("ExchangeOnlineManagement")

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
$credential = New-Object System.Management.Automation.PSCredential ($ServiceAccountUser, $securepass)


Write-Host "Connecting to Exchange Online and Graph API"
Write-Host "Connecting to Exchange Online"

try {
    Connect-ExchangeOnline -Credential $credential
    Write-Host "Successfully connected to Exchange Online"
} catch {
    Write-Host "ERROR: Failed to connect to Exchange Online. Error: $_"
}

Write-Host "Adding Litigation Hold to $UserAccount"
try {
    Set-Mailbox $UserAccount -LitigationHoldEnabled $true -LitigationHoldDuration 1825
    Write-Host "Successfully added Litigation Hold to $UserAccount"
} catch {
    Write-Host "ERROR: Failed to add Litigation Hold to $UserAccount. Error: $_"
}

Write-Host "Converting to Shared Mailbox"
try {
    Set-Mailbox $UserAccount -Type Shared
    Write-Host "Successfully converted $UserAccount to Shared Mailbox"
}
catch {
    Write-Host "ERROR: Failed to convert $UserAccount to Shared Mailbox. Error: $_"
}