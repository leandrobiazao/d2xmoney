# Test script for ticker mappings API
$baseUrl = "http://localhost:8000/api/ticker-mappings"

Write-Host "`n🧪 Testing Ticker Mappings API`n" -ForegroundColor Cyan

# Test 1: GET all mappings (should be empty initially)
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host "TEST 1: GET all ticker mappings" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Gray
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -ContentType "application/json"
    Write-Host "✅ Success! Found $($response.Count) mappings" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Gray
    $test1 = $true
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    $test1 = $false
}

# Test 2: POST create a mapping
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "TEST 2: POST create mapping (PETROBRAS ON NM -> PETR4)" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Gray
try {
    $body = @{
        nome = "PETROBRAS ON NM"
        ticker = "PETR4"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✅ Success! Mapping created" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 10)" -ForegroundColor Gray
    $test2 = $true
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    $test2 = $false
}

# Test 3: Check if file exists
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "TEST 3: Check if ticker.json file exists" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Gray
$filePath = "backend\data\ticker.json"
if (Test-Path $filePath) {
    Write-Host "✅ File exists at: $((Resolve-Path $filePath).Path)" -ForegroundColor Green
    try {
        $fileContent = Get-Content $filePath -Raw | ConvertFrom-Json
        Write-Host "✅ File contains $($fileContent.PSObject.Properties.Count) mappings:" -ForegroundColor Green
        Write-Host ($fileContent | ConvertTo-Json -Depth 10) -ForegroundColor Gray
        $test3 = $true
    } catch {
        Write-Host "❌ Error reading file: $_" -ForegroundColor Red
        $test3 = $false
    }
} else {
    Write-Host "❌ File does not exist at: $filePath" -ForegroundColor Red
    $test3 = $false
}

# Test 4: GET all mappings again (should have 1 now)
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "TEST 4: GET all ticker mappings (after creation)" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Gray
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -ContentType "application/json"
    Write-Host "✅ Success! Found $($response.PSObject.Properties.Count) mappings" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 10)" -ForegroundColor Gray
    $test4 = $true
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    $test4 = $false
}

# Test 5: GET specific mapping
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "TEST 5: GET specific mapping for 'PETROBRAS ON NM'" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Gray
try {
    $encodedNome = [System.Web.HttpUtility]::UrlEncode("PETROBRAS ON NM")
    $response = Invoke-RestMethod -Uri "$baseUrl/$encodedNome" -Method Get -ContentType "application/json"
    Write-Host "✅ Success! Mapping found" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 10)" -ForegroundColor Gray
    $test5 = $true
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    $test5 = $false
}

# Test 6: POST create another mapping
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "TEST 6: POST create mapping (VALE ON NM -> VALE3)" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Gray
try {
    $body = @{
        nome = "VALE ON NM"
        ticker = "VALE3"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✅ Success! Mapping created" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 10)" -ForegroundColor Gray
    $test6 = $true
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    $test6 = $false
}

# Check file again
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "TEST 7: Check file again (should have 2 mappings)" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Gray
if (Test-Path $filePath) {
    try {
        $fileContent = Get-Content $filePath -Raw | ConvertFrom-Json
        Write-Host "✅ File contains $($fileContent.PSObject.Properties.Count) mappings:" -ForegroundColor Green
        Write-Host ($fileContent | ConvertTo-Json -Depth 10) -ForegroundColor Gray
        $test7 = $true
    } catch {
        Write-Host "❌ Error reading file: $_" -ForegroundColor Red
        $test7 = $false
    }
} else {
    Write-Host "❌ File does not exist" -ForegroundColor Red
    $test7 = $false
}

# Summary
Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "GET all (initial): $(if ($test1) { '✅ PASS' } else { '❌ FAIL' })"
Write-Host "POST create (PETR4): $(if ($test2) { '✅ PASS' } else { '❌ FAIL' })"
Write-Host "File created: $(if ($test3) { '✅ PASS' } else { '❌ FAIL' })"
Write-Host "GET all (after): $(if ($test4) { '✅ PASS' } else { '❌ FAIL' })"
Write-Host "GET specific: $(if ($test5) { '✅ PASS' } else { '❌ FAIL' })"
Write-Host "POST create (VALE3): $(if ($test6) { '✅ PASS' } else { '❌ FAIL' })"
Write-Host "File updated: $(if ($test7) { '✅ PASS' } else { '❌ FAIL' })"

if ($test1 -and $test2 -and $test3 -and $test4 -and $test5 -and $test6 -and $test7) {
    Write-Host "`n🎉 All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n⚠️ Some tests failed. Check the output above." -ForegroundColor Yellow
    exit 1
}

