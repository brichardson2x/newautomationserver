param (
    [string]$ServiceAccountUser,
    [string]$ServicePass,
    [string]$UserAccount,
    [string]$AutoReplyMessage
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

Write-Host "Setting AutoReply for $UserAccount"
try {
    Set-MailboxAutoReplyConfiguration $UserAccount -AutoReplyState Enabled -InternalMessage $AutoReplyMessage -ExternalMessage $AutoReplyMessage -ExternalAudience All
    Write-Host "Successfully set Autoreply for $UserAccount"
} catch {
    Write-Host "ERROR: Failed to set Autoreply for $UserAccount. Error: $_"
}