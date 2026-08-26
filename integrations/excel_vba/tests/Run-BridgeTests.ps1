<#
.SYNOPSIS
    Fixture smoke test for the Excel bridge — the VBA half of the JSON interface.

.DESCRIPTION
    Builds a throwaway workbook in a hidden Excel instance, imports JsonConverter.bas,
    RysePricingBridge.bas and TestHarness.bas, lays out one bond in named cells, and
    checks the whole adapter path:

        cells -> request JSON (Excel date serials converted to ISO strings)
              -> a runner command, invoked and WAITED for
              -> response JSON -> output cells
              -> an error response -> message shown, stale numbers cleared

    The pricing itself is not re-tested here: it is covered by the Python suite
    (tests/test_vanilla_json_endpoint.py). The response used is the committed fixture
    examples/vanilla_response_v1.json, which IS real engine output, so the numbers
    checked below are the engine's numbers. A stand-in runner (a .cmd that copies the
    fixture to the --output path) stands in for Python, so this runs on a Windows desk
    with no Python installed.

    Requires Excel, and "Trust access to the VBA project object model". The script
    enables that setting for the duration of the run and restores its previous state
    in the finally block, whatever happens.

    Two notes for anyone extending this: all cell I/O lives in TestHarness.bas rather
    than here, because the PowerShell COM binder types a property from its first use
    per call site (write a string then a double to the same site and it throws); and
    the harness never calls the bridge's MsgBox paths, since a modal dialog in an
    invisible Excel would hang the run.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File integrations\excel_vba\tests\Run-BridgeTests.ps1
#>

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bridge = Split-Path -Parent $here
$examples = Join-Path $bridge "examples"
$temp = $env:TEMP
$secKey = "HKCU:\Software\Microsoft\Office\16.0\Excel\Security"
$inv = [Globalization.CultureInfo]::InvariantCulture

$results = New-Object System.Collections.ArrayList
function Check($name, $ok, $detail) {
    $tag = if ($ok) { "PASS" } else { "FAIL" }
    [void]$results.Add([pscustomobject]@{ Check = $name; Result = $tag; Detail = $detail })
    "{0}  {1,-34} {2}" -f $tag, $name, $detail
}
function Near($text, $expected, $tol) {
    if ([string]::IsNullOrEmpty($text)) { return $false }
    $v = 0.0
    if (-not [double]::TryParse($text, [Globalization.NumberStyles]::Float, $inv, [ref]$v)) { return $false }
    return [math]::Abs($v - $expected) -lt $tol
}

$hadVbom = $false
$oldVbom = $null
if (Test-Path $secKey) {
    $existing = Get-ItemProperty $secKey
    if ($null -ne $existing.AccessVBOM) { $hadVbom = $true; $oldVbom = $existing.AccessVBOM }
}
$excelBefore = @(Get-Process EXCEL -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$excel = $null
$wb = $null

try {
    if (-not (Test-Path $secKey)) { New-Item -Path $secKey -Force | Out-Null }
    Set-ItemProperty -Path $secKey -Name AccessVBOM -Value 1 -Type DWord
    "AccessVBOM temporarily set to 1 (was: $(if ($hadVbom) { $oldVbom } else { 'not set' }))"
    ""

    $fakeRunner = Join-Path $temp "ryse_fake_runner.cmd"
    $canned = Join-Path $examples "vanilla_response_v1.json"
    @("@echo off", "copy /Y `"$canned`" %4 >nul", "exit /b 0") |
        Set-Content -Path $fakeRunner -Encoding ascii

    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $wb = $excel.Workbooks.Add()

    $wb.VBProject.VBComponents.Import((Join-Path $bridge "JsonConverter.bas")) | Out-Null
    $wb.VBProject.VBComponents.Import((Join-Path $bridge "RysePricingBridge.bas")) | Out-Null
    $wb.VBProject.VBComponents.Import((Join-Path $here "TestHarness.bas")) | Out-Null
    # Microsoft Scripting Runtime — VBA-JSON declares Dictionary.
    $wb.VBProject.References.AddFromGuid("{420B2830-E718-11CF-893D-00A0C9054228}", 1, 0) | Out-Null
    Check "modules import + Scripting ref" $true "JsonConverter, RysePricingBridge, harness"

    $excel.Run("Harness_Setup", $fakeRunner) | Out-Null
    Check "sheet laid out and named" $true "10 input names, 14 output names, real date cells"

    # --- 1. what the sheet actually sends --------------------------------------------
    $requestPath = Join-Path $temp "ryse_test_request.json"
    if (Test-Path $requestPath) { Remove-Item $requestPath }
    $excel.Run("Harness_WriteRequest", $requestPath) | Out-Null
    $request = Get-Content $requestPath -Raw | ConvertFrom-Json

    Check "request written from cells" (Test-Path $requestPath) "$((Get-Item $requestPath).Length) bytes of JSON"
    Check "Excel serial -> ISO maturity" ($request.bond.maturity_date -eq "2017-01-15") `
        "cell held serial 42750, sent `"$($request.bond.maturity_date)`""
    Check "Excel serial -> ISO valuation" ($request.market.valuation_date -eq "2009-03-31") `
        "cell held serial 39903, sent `"$($request.market.valuation_date)`""
    Check "economics carried" `
        (($request.bond.coupon_pct -eq 6.5) -and ($request.market.clean_price_per_100 -eq 94.25) -and ($request.bond.coupon_frequency -eq 2)) `
        "coupon $($request.bond.coupon_pct), price $($request.market.clean_price_per_100), freq $($request.bond.coupon_frequency)"
    Check "currency upper-cased" ($request.bond.currency -eq "USD") `
        "cell contained 'usd', sent '$($request.bond.currency)'"
    Check "volatility passed through" ($request.model.yield_volatility_decimal -eq 0.15) `
        "model.yield_volatility_decimal $($request.model.yield_volatility_decimal)"

    # --- 2. the whole adapter path, through a command it must wait for ----------------
    $responsePath = Join-Path $temp "ryse_test_response.json"
    if (Test-Path $responsePath) { Remove-Item $responsePath }
    $exitCode = $excel.Run("Harness_RoundTrip", (Join-Path $temp "ryse_test_request2.json"), $responsePath)
    Check "runner invoked and waited for" ((Test-Path $responsePath) -and ($exitCode -eq 0)) `
        "exit code $exitCode; response file present when Run returned"

    $status = $excel.Run("Harness_Get", "FIP_Status")
    Check "status cell" ($status -eq "ok") "FIP_Status = $status"
    $clean = $excel.Run("Harness_Get", "FIP_ModelCleanPrice")
    Check "clean price mapped" (Near $clean 94.24999999411493 1e-9) $clean
    $dirty = $excel.Run("Harness_Get", "FIP_ModelDirtyPrice")
    $accrued = $excel.Run("Harness_Get", "FIP_AccruedInterest")
    Check "dirty + accrued mapped" ((Near $dirty 95.41071427982922 1e-9) -and (Near $accrued 1.1607142857142858 1e-12)) `
        "$dirty / $accrued"
    $oas = $excel.Run("Harness_Get", "FIP_ImpliedOASBp")
    Check "implied OAS mapped" (Near $oas 523.2980448854493 1e-9) "$oas bp"
    $dur = $excel.Run("Harness_Get", "FIP_EffectiveDuration")
    Check "duration mapped" (Near $dur 6.090692137822485 1e-12) "$dur y"
    $dv01 = $excel.Run("Harness_Get", "FIP_DV01")
    Check "DV01 mapped" (Near $dv01 0.058111728732818335 1e-15) $dv01
    $cvx = $excel.Run("Harness_Get", "FIP_Convexity")
    Check "convexity mapped" (Near $cvx 43.43704394133383 1e-10) $cvx
    $tight = $excel.Run("Harness_Get", "FIP_TighterPrice")
    $wide = $excel.Run("Harness_Get", "FIP_WiderPrice")
    Check "scenario prices mapped" ((Near $tight 94.83319457648531 1e-9) -and (Near $wide 93.6709497905553 1e-9)) `
        "tighter $tight / wider $wide"
    $curve = $excel.Run("Harness_Get", "FIP_CurveId")
    Check "curve id mapped" ($curve -eq "USD|2009-03-31|Semiannual") $curve
    $volNote = $excel.Run("Harness_Get", "FIP_VolatilityApplicability")
    Check "volatility applicability shown" ($volNote -like "not used by vanilla*") `
        "$($volNote.Substring(0, [math]::Min(52, $volNote.Length)))..."
    $errCell = $excel.Run("Harness_Get", "FIP_Errors")
    Check "no spurious errors" ([string]::IsNullOrEmpty($errCell)) "FIP_Errors empty"

    # --- 3. an error response ---------------------------------------------------------
    # Regression guard: "applicability" is JSON null here, which reaches VBA as Null
    # (not Nothing). Before 2026-08-25 this raised "Object required" and the sheet
    # never showed the error at all.
    $excel.Run("Harness_Populate", (Join-Path $examples "vanilla_error_v1.json")) | Out-Null
    $status2 = $excel.Run("Harness_Get", "FIP_Status")
    Check "error status shown" ($status2 -eq "error") "FIP_Status = $status2"
    $err2 = $excel.Run("Harness_Get", "FIP_Errors")
    Check "error message shown" ($err2 -like "CURVE_NOT_FOUND*") `
        "$($err2.Substring(0, [math]::Min(62, $err2.Length)))..."
    $clean2 = $excel.Run("Harness_Get", "FIP_ModelCleanPrice")
    $oas2 = $excel.Run("Harness_Get", "FIP_ImpliedOASBp")
    Check "stale numbers cleared" (([string]::IsNullOrEmpty($clean2)) -and ([string]::IsNullOrEmpty($oas2))) `
        "price and OAS blanked, not left showing the previous bond"

    ""
    $passed = ($results | Where-Object Result -eq 'PASS').Count
    "$passed/$($results.Count) checks passed"
    if ($passed -ne $results.Count) { "FAILURES PRESENT"; exit 1 }
}
finally {
    if ($null -ne $wb) { try { $wb.Close($false) } catch {} }
    if ($null -ne $excel) { try { $excel.Quit() } catch {} }
    if ($null -ne $excel) { try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) } catch {} }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()

    # Only Excel processes this script started.
    Get-Process EXCEL -ErrorAction SilentlyContinue |
        Where-Object { $excelBefore -notcontains $_.Id } |
        ForEach-Object { try { Stop-Process -Id $_.Id -Force } catch {} }

    if ($hadVbom) {
        Set-ItemProperty -Path $secKey -Name AccessVBOM -Value $oldVbom -Type DWord
        "AccessVBOM restored to $oldVbom"
    } else {
        try { Remove-ItemProperty -Path $secKey -Name AccessVBOM -ErrorAction Stop } catch {}
        "AccessVBOM removed (restored to 'not set')"
    }
}
