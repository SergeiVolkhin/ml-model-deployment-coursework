<#
.SYNOPSIS
Create/update Telegram contact point and notification policy in Grafana via REST API.

.DESCRIPTION
Alternative to file-based provisioning. Solves a type-coercion problem: Grafana
env-substitution into provisioning YAML either turns chatid into a JSON number
(unmarshal into Go string fails) or wraps it in literal quotes (Telegram returns
400 because chat_id is invalid). The REST endpoint takes explicit JSON where
chatid is sent as a plain string over HTTP, bypassing YAML and Go marshaling.

.PARAMETER GrafanaUrl
Grafana URL (default http://localhost:3000).

.PARAMETER AdminUser, AdminPass
Admin credentials (default admin/admin matching docker-compose env).

.PARAMETER EnvFile
Path to .env with TG_BOT_TOKEN and TG_CHAT_ID (default .env in current dir).

.EXAMPLE
.\scripts\setup_grafana_telegram.ps1
.\scripts\setup_grafana_telegram.ps1 -GrafanaUrl http://localhost:3000 -EnvFile .\.env
#>
[CmdletBinding()]
param(
    [string]$GrafanaUrl = "http://localhost:3000",
    [string]$AdminUser = "admin",
    [string]$AdminPass = "admin",
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    Write-Error "File $EnvFile not found. Run 'Copy-Item .env.example .env' and fill in TG_BOT_TOKEN/TG_CHAT_ID first."
    exit 1
}

$envMap = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and ($line -match '^([A-Z_][A-Z0-9_]*)=(.*)$')) {
        $key = $matches[1]
        $val = $matches[2].Trim()
        if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        $envMap[$key] = $val
    }
}

foreach ($k in @("TG_BOT_TOKEN", "TG_CHAT_ID")) {
    if (-not $envMap.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($envMap[$k]) -or $envMap[$k] -like "<your_*>") {
        Write-Error "No valid $k in $EnvFile. Put the real value and re-run."
        exit 1
    }
}

$botToken = $envMap["TG_BOT_TOKEN"]
$chatId = $envMap["TG_CHAT_ID"]

Write-Host "Validating TG_BOT_TOKEN via Telegram getMe..." -ForegroundColor Cyan
try {
    $me = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getMe" -Method GET
    if (-not $me.ok) { throw "getMe returned ok=false: $($me | ConvertTo-Json -Compress)" }
    Write-Host "  bot: @$($me.result.username) (id=$($me.result.id))" -ForegroundColor Green
} catch {
    Write-Error "TG_BOT_TOKEN invalid (Telegram API: $_). Get a fresh token from @BotFather and update $EnvFile."
    exit 1
}

$messageTemplate = @'
<b>{{ .CommonAnnotations.summary }}</b>
{{ range .Alerts }}
<code>{{ .Labels.alertname }}</code> @ <code>{{ .Labels.service }}</code>
severity: {{ .Labels.severity }}
{{ .Annotations.description }}
{{ end }}
'@

$contactPoint = [ordered]@{
    uid                   = "tg-hw8"
    name                  = "telegram-hw8"
    type                  = "telegram"
    disableResolveMessage = $false
    settings              = [ordered]@{
        bottoken   = $botToken
        chatid     = "$chatId"
        parse_mode = "HTML"
        message    = $messageTemplate
    }
}
$contactPointBody = $contactPoint | ConvertTo-Json -Depth 6 -Compress

$policy = [ordered]@{
    receiver        = "telegram-hw8"
    group_by        = @("alertname", "service")
    group_wait      = "30s"
    group_interval  = "1m"
    repeat_interval = "10m"
}
$policyBody = $policy | ConvertTo-Json -Depth 8 -Compress

$cred = "{0}:{1}" -f $AdminUser, $AdminPass
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($cred))
$headers = @{
    Authorization          = "Basic $basic"
    "Content-Type"         = "application/json"
    "X-Disable-Provenance" = "true"
}

Write-Host "Applying contact point telegram-hw8..." -ForegroundColor Cyan
try {
    $null = Invoke-RestMethod -Uri "$GrafanaUrl/api/v1/provisioning/contact-points/tg-hw8" `
        -Method PUT -Headers $headers -Body $contactPointBody
    Write-Host "  contact point updated" -ForegroundColor Green
} catch {
    $statusCode = $null
    if ($_.Exception.Response) { $statusCode = [int]$_.Exception.Response.StatusCode }
    if ($statusCode -eq 404) {
        $null = Invoke-RestMethod -Uri "$GrafanaUrl/api/v1/provisioning/contact-points" `
            -Method POST -Headers $headers -Body $contactPointBody
        Write-Host "  contact point created" -ForegroundColor Green
    } else {
        Write-Error "Failed to apply contact point: $_"
        exit 1
    }
}

Write-Host "Applying notification policy (severity=warning -> telegram)..." -ForegroundColor Cyan
try {
    $null = Invoke-RestMethod -Uri "$GrafanaUrl/api/v1/provisioning/policies" `
        -Method PUT -Headers $headers -Body $policyBody
    Write-Host "  policy updated" -ForegroundColor Green
} catch {
    Write-Error "Failed to apply policy: $_"
    exit 1
}

Write-Host ""
Write-Host "Done. Open Grafana -> Alerting -> Contact points -> telegram-hw8 -> Test." -ForegroundColor Green
Write-Host "If message does not arrive, double-check TG_CHAT_ID via @userinfobot." -ForegroundColor Yellow
