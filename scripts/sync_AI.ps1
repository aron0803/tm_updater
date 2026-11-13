# 1. Path Definitions
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$ClaudeDir = Join-Path $ProjectRoot ".claude\commands"
$SyncTarget = Join-Path $ProjectRoot "scripts\ai_skills"
$AntigravityDir = Join-Path $ProjectRoot ".agent\skills"
$AgentDir = Join-Path $ProjectRoot ".agent"

Write-Host "--- AI Config Sync Starting ---" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot"

# 2. Create Directories
if (!(Test-Path $SyncTarget)) { New-Item -ItemType Directory -Path $SyncTarget -Force }
if (!(Test-Path $AgentDir)) { New-Item -ItemType Directory -Path $AgentDir -Force }

# 3. Sync CLAUDE.md to AGENT.md
$ClaudeMd = Join-Path $ProjectRoot "CLAUDE.md"
$AgentMd = Join-Path $AgentDir "AGENT.md"

if (Test-Path $ClaudeMd) {
    Write-Host "Linking Project Rules..."
    if (Test-Path $AgentMd) { Remove-Item $AgentMd -Force }
    New-Item -ItemType SymbolicLink -Path $AgentMd -Target $ClaudeMd -Force
}

# 4. Helper Function for Linking Folders
function Create-Link-Folder($LinkPath, $TargetPath) {
    if (Test-Path $LinkPath) {
        $item = Get-Item $LinkPath
        # Check if it is a directory or a symlink, then remove
        Remove-Item $LinkPath -Recurse -Force
    }
    New-Item -ItemType SymbolicLink -Path $LinkPath -Target $TargetPath -Force
}

# 5. Execute Linking
Write-Host "Linking Claude Commands..."
Create-Link-Folder -LinkPath $ClaudeDir -TargetPath $SyncTarget

Write-Host "Linking Antigravity Skills..."
Create-Link-Folder -LinkPath $AntigravityDir -TargetPath $SyncTarget

Write-Host "--------------------------------" -ForegroundColor Green
Write-Host "SUCCESS: AI configuration folders are now synchronized."
Write-Host "Target location: $SyncTarget"