$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhMjc4YWM4Yi0yZmJmLTQ1ZGQtODAxMS1jODM3OWU0N2FkMjgiLCJlbWFpbCI6ImFkbWluQGZpbGVtYW5hZ2VyLmNvbSIsInJvbGUiOiJzdXBlcl9hZG1pbiIsIm9yZ19pZCI6bnVsbCwicGVybWlzc2lvbnMiOlsiZmlsZTpyZWFkIiwiZmlsZTp3cml0ZSIsImZpbGU6ZGVsZXRlIiwiZmlsZTpzaGFyZSIsInVzZXI6cmVhZCIsInVzZXI6d3JpdGUiLCJ1c2VyOmRlbGV0ZSIsIm9yZzpyZWFkIiwib3JnOndyaXRlIiwib3JnOmFkbWluIiwicGlwZWxpbmU6cmVhZCIsInBpcGVsaW5lOmV4ZWN1dGUiLCJwaXBlbGluZTp0cmFpbiIsInBpcGVsaW5lOmFkbWluIiwiYW5hbHl0aWNzOnJlYWQiLCJhbmFseXRpY3M6ZXhwb3J0Iiwic3lzdGVtOmFkbWluIiwic3lzdGVtOmNvbmZpZyJdLCJleHAiOjE3NjczMzc1MTUsImlhdCI6MTc2NzMzMzkxNSwidHlwZSI6ImFjY2VzcyJ9.bx7iTGX7s2gg9i6PYB-deGlAtRB_WHRVuOezx1MPkbI"

$questions = @(
    # USERS
    "list all users",
    "how many users are there",
    "show me all super admins",
    "users with pending status",
    
    # FILES
    "list all files",
    "how many files are uploaded",
    "largest files",
    "average file size",
    "files larger than 1MB",
    "PDF files only",
    
    # ORGANIZATIONS
    "list all organizations",
    "how many organizations",
    "active organizations",
    
    # FOLDERS
    "list all folders",
    
    # CROSS-TABLE JOINS
    "users in organization vedirobotics",
    "files uploaded by Super Admin",
    "users per organization",
    "files per user",
    "who uploaded the most files",
    "which organization has most files",
    "users with their organization names",
    
    # EDGE CASES
    "users without organization",
    "files without folder",
    "empty organizations"
)

$pass = 0
$fail = 0
$results = @()

foreach ($q in $questions) {
    Write-Host "Testing: $q" -NoNewline
    $body = "{`"message`": `"$q`"}"
    $resp = curl -s -X POST "http://localhost:8000/api/v1/chat/" -H "Content-Type: application/json" -H "Authorization: Bearer $token" -d $body
    
    if ($resp -match "OperationalError|Unknown column|error.*SQL|couldn't find that") {
        Write-Host " [FAIL]" -ForegroundColor Red
        $fail++
        $results += [PSCustomObject]@{Q=$q; Status="FAIL"; Resp=$resp.Substring(0, [Math]::Min(200, $resp.Length))}
    } else {
        Write-Host " [PASS]" -ForegroundColor Green
        $pass++
        $results += [PSCustomObject]@{Q=$q; Status="PASS"; Resp="OK"}
    }
    Start-Sleep -Seconds 2
}

Write-Host "`n========== RESULTS ==========" -ForegroundColor Yellow
Write-Host "PASS: $pass / $($questions.Count)" -ForegroundColor Green
Write-Host "FAIL: $fail / $($questions.Count)" -ForegroundColor Red

Write-Host "`n========== FAILURES ==========" -ForegroundColor Red
$results | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
    Write-Host "`nQ: $($_.Q)" -ForegroundColor Cyan
    Write-Host "Error: $($_.Resp)" -ForegroundColor Red
}
