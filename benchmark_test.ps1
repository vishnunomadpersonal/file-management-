# Chatbot Benchmark Test Script
# Run: .\benchmark_test.ps1

param(
    [string]$Token = ""
)

if (-not $Token) {
    $loginBody = '{"email": "Admin@filemanager.com", "password": "Admin1234"}'
    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
    $Token = $loginResponse.data.access_token
}

$headers = @{ "Authorization" = "Bearer $Token"; "Content-Type" = "application/json" }

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════╗"
Write-Host "║           CHATBOT PRODUCTION BENCHMARK TEST                      ║"
Write-Host "║           $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                                  ║"
Write-Host "╚══════════════════════════════════════════════════════════════════╝"
Write-Host ""

# Ground Truth from Database:
# users: 25, files: 15, organizations: 12, folders: 1
# total_storage: 2.77 MB
# Super Admin: 5 files, 1.65 MB | user20: 10 files, 1.12 MB
# files in Dec 2025 - Jan 2026: 15

$allResults = @()

function Test-Query {
    param($Query, $Expected, $Type)
    
    $body = '{"message": "' + $Query + '"}'
    $start = Get-Date
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat/" -Method POST -Headers $headers -Body $body -TimeoutSec 120
        $elapsed = [int]((Get-Date) - $start).TotalMilliseconds
        $answer = $r.response.message
        $routing = $r.routing.method
        $contains = $answer -match $Expected
        
        return @{
            Query = $Query
            Expected = $Expected
            Type = $Type
            Routing = $routing
            Pass = $contains
            TimeMs = $elapsed
            Answer = $answer.Substring(0, [Math]::Min(80, $answer.Length))
        }
    } catch {
        return @{
            Query = $Query
            Expected = $Expected
            Type = $Type
            Routing = "ERROR"
            Pass = $false
            TimeMs = 0
            Answer = $_.Exception.Message
        }
    }
}

# ============ BATCH 1: Simple Count Queries ============
Write-Host "┌─────────────────────────────────────────────────────────────────┐"
Write-Host "│ BATCH 1: Simple Count Queries (Template SQL)                    │"
Write-Host "└─────────────────────────────────────────────────────────────────┘"

$batch1 = @(
    @("how many users", "25", "count"),
    @("how many files", "15", "count"),
    @("total storage", "2.77", "count"),
    @("how many organizations", "12", "count"),
    @("count users", "25", "count"),
    @("number of files", "15", "count"),
    @("user count", "25", "count"),
    @("file count", "15", "count")
)

foreach ($t in $batch1) {
    $result = Test-Query -Query $t[0] -Expected $t[1] -Type $t[2]
    $status = if ($result.Pass) { "✓ PASS" } else { "✗ FAIL" }
    Write-Host "$status | $($t[0]) | exp: $($t[1]) | $($result.Routing) | $($result.TimeMs)ms"
    $allResults += $result
}

# ============ BATCH 2: Synonym/Casual Queries ============
Write-Host ""
Write-Host "┌─────────────────────────────────────────────────────────────────┐"
Write-Host "│ BATCH 2: Synonym & Casual Language Queries                      │"
Write-Host "└─────────────────────────────────────────────────────────────────┘"

$batch2 = @(
    @("how many folks in the platform", "25", "synonym"),
    @("how many documents", "15", "synonym"),
    @("documents added", "15", "synonym"),
    @("total space used", "2.77", "synonym"),
    @("show me user count", "25", "synonym"),
    @("whats the file count", "15", "synonym"),
    @("people registered", "25", "synonym"),
    @("uploads count", "15", "synonym")
)

foreach ($t in $batch2) {
    $result = Test-Query -Query $t[0] -Expected $t[1] -Type $t[2]
    $status = if ($result.Pass) { "✓ PASS" } else { "✗ FAIL" }
    Write-Host "$status | $($t[0]) | exp: $($t[1]) | $($result.Routing) | $($result.TimeMs)ms"
    $allResults += $result
}

# ============ BATCH 3: Complex LLM Queries ============
Write-Host ""
Write-Host "┌─────────────────────────────────────────────────────────────────┐"
Write-Host "│ BATCH 3: Complex LLM Queries (Text-to-SQL)                      │"
Write-Host "└─────────────────────────────────────────────────────────────────┘"

$batch3 = @(
    @("which users have the most storage sorted by total file size", "Super Admin", "llm_ranking"),
    @("documents uploaded between December 2025 and January 2026", "user20", "llm_date"),
    @("top users by file count", "user20", "llm_ranking"),
    @("list files uploaded in December 2025", "2025-12", "llm_date"),
    @("users with most files", "user20", "llm_ranking")
)

foreach ($t in $batch3) {
    $result = Test-Query -Query $t[0] -Expected $t[1] -Type $t[2]
    $status = if ($result.Pass) { "✓ PASS" } else { "✗ FAIL" }
    Write-Host "$status | $($t[0].Substring(0, [Math]::Min(50, $t[0].Length)))... | exp: $($t[1]) | $($result.Routing) | $($result.TimeMs)ms"
    $allResults += $result
}

# ============ BATCH 4: Navigation/Help Queries ============
Write-Host ""
Write-Host "┌─────────────────────────────────────────────────────────────────┐"
Write-Host "│ BATCH 4: Navigation & Help Queries (Rule-based)                 │"
Write-Host "└─────────────────────────────────────────────────────────────────┘"

$batch4 = @(
    @("hello", "hello|hi|welcome|help", "greeting"),
    @("help", "help|can|assist", "greeting"),
    @("what can you do", "can|help|assist|analytics", "greeting")
)

foreach ($t in $batch4) {
    $result = Test-Query -Query $t[0] -Expected $t[1] -Type $t[2]
    $status = if ($result.Pass) { "✓ PASS" } else { "✗ FAIL" }
    Write-Host "$status | $($t[0]) | $($result.Routing) | $($result.TimeMs)ms"
    $allResults += $result
}

# ============ SUMMARY ============
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════╗"
Write-Host "║                    BENCHMARK SUMMARY                             ║"
Write-Host "╚══════════════════════════════════════════════════════════════════╝"

$totalTests = $allResults.Count
$passedTests = ($allResults | Where-Object { $_.Pass }).Count
$failedTests = $totalTests - $passedTests
$accuracy = [math]::Round(($passedTests / $totalTests) * 100, 1)

Write-Host ""
Write-Host "Total Tests:    $totalTests"
Write-Host "Passed:         $passedTests ✓"
Write-Host "Failed:         $failedTests ✗"
Write-Host "Accuracy:       $accuracy%"
Write-Host ""

# By Type
Write-Host "─── By Query Type ───"
$allResults | Group-Object Type | ForEach-Object {
    $typePass = ($_.Group | Where-Object { $_.Pass }).Count
    $typeTotal = $_.Count
    $pct = [math]::Round(($typePass / $typeTotal) * 100, 0)
    Write-Host "  $($_.Name): $typePass/$typeTotal ($pct%)"
}

Write-Host ""
Write-Host "─── By Routing Method ───"
$allResults | Group-Object Routing | ForEach-Object {
    $avgTime = [math]::Round(($_.Group | Measure-Object -Property TimeMs -Average).Average, 0)
    $routePass = ($_.Group | Where-Object { $_.Pass }).Count
    Write-Host "  $($_.Name): $routePass/$($_.Count) passed, avg ${avgTime}ms"
}

Write-Host ""
Write-Host "─── Performance ───"
$templateAvg = [math]::Round(($allResults | Where-Object { $_.Routing -eq "analytics_template_sql" } | Measure-Object -Property TimeMs -Average).Average, 0)
$llmAvg = [math]::Round(($allResults | Where-Object { $_.Routing -eq "text_to_sql_llm" } | Measure-Object -Property TimeMs -Average).Average, 0)
Write-Host "  Template SQL avg: ${templateAvg}ms"
Write-Host "  Text-to-SQL LLM avg: ${llmAvg}ms"

# Final verdict
Write-Host ""
if ($accuracy -ge 90) {
    Write-Host "═══════════════════════════════════════════════════════════════════"
    Write-Host "  ✓ PRODUCTION READY - $accuracy% accuracy achieved!"
    Write-Host "═══════════════════════════════════════════════════════════════════"
} elseif ($accuracy -ge 80) {
    Write-Host "═══════════════════════════════════════════════════════════════════"
    Write-Host "  ⚠ ACCEPTABLE - $accuracy% accuracy, needs improvement"
    Write-Host "═══════════════════════════════════════════════════════════════════"
} else {
    Write-Host "═══════════════════════════════════════════════════════════════════"
    Write-Host "  ✗ NOT READY - $accuracy% accuracy, requires fixes"
    Write-Host "═══════════════════════════════════════════════════════════════════"
}

# Show failures
$failures = $allResults | Where-Object { -not $_.Pass }
if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "─── Failed Tests ───"
    foreach ($f in $failures) {
        Write-Host "  ✗ $($f.Query)"
        Write-Host "    Expected: $($f.Expected)"
        Write-Host "    Got: $($f.Answer)..."
    }
}
