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

    Two modes:

      default        a stand-in runner (a .cmd that copies the committed fixture to the
                     --output path) plays the part of the engine, so the VBA can be
                     tested on a Windows desk with no Python installed at all. The
                     fixture IS real engine output, so the numbers checked are the
                     engine's numbers.
      -PythonExe     the real thing: a runner is generated that calls
                     scripts/price_json.py with the interpreter you name, so Excel
                     prices the bond live. Same expected numbers, since the engine is
                     deterministic across platforms.

    Either way the pricing itself is covered by the Python suite
    (tests/test_vanilla_json_endpoint.py); what this script tests is the VBA adapter.

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

.EXAMPLE
    # end to end, with Excel calling Python for real
    powershell -ExecutionPolicy Bypass -File integrations\excel_vba\tests\Run-BridgeTests.ps1 `
        -PythonExe C:\Users\cnc\anaconda3\anaconda2025\python.exe
#>
param(
    [string]$PythonExe = ""      # empty: use the stand-in runner (no Python needed)
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bridge = Split-Path -Parent $here
$repo = Split-Path -Parent (Split-Path -Parent $bridge)
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

    $runnerPath = Join-Path $temp "ryse_test_runner.cmd"
    if ($PythonExe) {
        if (-not (Test-Path $PythonExe)) { throw "PythonExe not found: $PythonExe" }
        @("@echo off",
          "cd /d `"$repo`" || exit /b 2",
          "set PYTHONPATH=src",
          "`"$PythonExe`" scripts\price_json.py %*") |
            Set-Content -Path $runnerPath -Encoding ascii
        "runner: LIVE - $PythonExe against $repo"
    } else {
        $canned = Join-Path $examples "vanilla_response_v1.json"
        @("@echo off", "copy /Y `"$canned`" %4 >nul", "exit /b 0") |
            Set-Content -Path $runnerPath -Encoding ascii
        "runner: stand-in (returns the committed fixture; no Python required)"
    }

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

    $excel.Run("Harness_Setup", $runnerPath) | Out-Null
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
    $mode = if ($PythonExe) { "live Python priced it" } else { "stand-in runner" }
    Check "runner invoked and waited for" ((Test-Path $responsePath) -and ($exitCode -eq 0)) `
        "exit code $exitCode; response present when Run returned ($mode)"

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

    # === 4. instrument types: callable, puttable, sinking (2026-08-31) ================
    # Everything above is the original vanilla suite, run unchanged. From here the same
    # bridge is driven with a type named, which is the only difference between the two.
    $excel.Run("Harness_SetupTypes") | Out-Null
    Check "type inputs + schedule tables laid out" $true `
        "FIP_InstrumentType/Operation/OASBp/SinkingFractionBasis + 3 named Tables"

    function Get-Request($path) {
        $excel.Run("Harness_WriteRequest", $path) | Out-Null
        Get-Content $path -Raw | ConvertFrom-Json
    }

    # --- 4.1 callable: the request the sheet builds -----------------------------------
    $excel.Run("Harness_SetText", "FIP_InstrumentType", "callable") | Out-Null
    $excel.Run("Harness_SetNumber", "FIP_CouponPct", "9.5") | Out-Null
    $excel.Run("Harness_SetNumber", "FIP_CleanMarketPrice", "104") | Out-Null
    $excel.Run("Harness_SetDate", "FIP_MaturityDate", "2014-04-01") | Out-Null
    $excel.Run("Harness_SetSchedule", "FIP_CallSchedule", "2011-04-01|100;2012-04-01|100") | Out-Null

    $reqPath = Join-Path $temp "ryse_callable_request.json"
    $req = Get-Request $reqPath
    Check "instrument type serialised" ($req.bond.instrument_type -eq "callable") `
        "bond.instrument_type = $($req.bond.instrument_type)"
    Check "schema version follows the type" ($req.schema_version -eq "1.1") `
        "schema_version = $($req.schema_version)"
    Check "call schedule is an ordered array" `
        (($req.bond.call_schedule.Count -eq 2) -and `
         ($req.bond.call_schedule[0].date -eq "2011-04-01") -and `
         ($req.bond.call_schedule[1].date -eq "2012-04-01")) `
        "2 rows, first $($req.bond.call_schedule[0].date), then $($req.bond.call_schedule[1].date)"
    Check "schedule dates are ISO strings" `
        (($req.bond.call_schedule[0].date -is [string]) -and `
         ($req.bond.call_schedule[0].date -match '^\d{4}-\d{2}-\d{2}$')) `
        "typed as $($req.bond.call_schedule[0].date.GetType().Name), value $($req.bond.call_schedule[0].date)"
    $rawJson = Get-Content $reqPath -Raw
    Check "no Excel date serial anywhere in the JSON" `
        (-not ($rawJson -match '"date"\s*:\s*\d')) "grep for a numeric date field found none"
    Check "prices per 100 carried" ($req.bond.call_schedule[0].price_per_100 -eq 100) `
        "price_per_100 = $($req.bond.call_schedule[0].price_per_100)"
    Check "blank table rows ignored" ($req.bond.call_schedule.Count -eq 2) `
        "table has 6 data rows, 2 filled, 2 sent"
    Check "empty optional tables omitted" `
        ((-not ($req.bond.PSObject.Properties.Name -contains "put_schedule")) -and `
         (-not ($req.bond.PSObject.Properties.Name -contains "sinking_schedule"))) `
        "put and sinking tables are empty, so neither field is sent"
    Check "calibrating operation sends no OAS" `
        (-not ($req.analysis.PSObject.Properties.Name -contains "oas_bp")) `
        "calibrate_and_risk refuses a supplied spread, so the bridge does not send one"

    # --- 4.2 both operations, from the sheet ------------------------------------------
    $excel.Run("Harness_SetText", "FIP_Operation", "price_at_oas") | Out-Null
    $excel.Run("Harness_SetNumber", "FIP_OASBp", "400") | Out-Null
    $req2 = Get-Request (Join-Path $temp "ryse_callable_oas_request.json")
    Check "price_at_oas sends the chosen spread" `
        (($req2.operation -eq "price_at_oas") -and ($req2.analysis.oas_bp -eq 400)) `
        "operation $($req2.operation), analysis.oas_bp $($req2.analysis.oas_bp)"
    $excel.Run("Harness_SetText", "FIP_Operation", "calibrate_and_risk") | Out-Null
    $req3 = Get-Request (Join-Path $temp "ryse_callable_calib_request.json")
    Check "the OAS cell is ignored when calibrating" `
        (-not ($req3.analysis.PSObject.Properties.Name -contains "oas_bp")) `
        "FIP_OASBp still holds 400, and is deliberately not sent"

    # --- 4.3 combined rights, and row order -------------------------------------------
    $excel.Run("Harness_SetSchedule", "FIP_PutSchedule", "2012-04-01|100") | Out-Null
    $req4 = Get-Request (Join-Path $temp "ryse_combined_request.json")
    Check "call and put transmitted together" `
        (($req4.bond.call_schedule.Count -eq 2) -and ($req4.bond.put_schedule.Count -eq 1)) `
        "call 2 rows, put 1 row, one request"
    $excel.Run("Harness_SetSchedule", "FIP_CallSchedule", "2012-04-01|100;2011-04-01|100") | Out-Null
    $req5 = Get-Request (Join-Path $temp "ryse_order_request.json")
    Check "row order preserved, not sorted" `
        (($req5.bond.call_schedule[0].date -eq "2012-04-01") -and `
         ($req5.bond.call_schedule[1].date -eq "2011-04-01")) `
        "sheet order kept; sorting is the engine's job, not the bridge's"
    $excel.Run("Harness_SetSchedule", "FIP_CallSchedule", "2011-04-01|100;2012-04-01|100") | Out-Null
    $excel.Run("Harness_ClearSchedule", "FIP_PutSchedule") | Out-Null

    # --- 4.4 a partly filled row fails in Excel, before Python is ever called ----------
    $excel.Run("Harness_SetSchedule", "FIP_CallSchedule", "2011-04-01|100;2012-04-01|") | Out-Null
    $vbaErr = $excel.Run("Harness_TryWriteRequest", (Join-Path $temp "ryse_bad_request.json"))
    Check "partly filled row refused in Excel" `
        (($vbaErr -like "*FIP_CallSchedule*") -and ($vbaErr -like "*row 2*")) `
        "$($vbaErr.Substring(0, [math]::Min(64, $vbaErr.Length)))..."
    $excel.Run("Harness_SetSchedule", "FIP_CallSchedule", "2011-04-01|100;2012-04-01|100") | Out-Null

    # --- 4.5 sinking: three columns, and the basis --------------------------------------
    $excel.Run("Harness_SetText", "FIP_InstrumentType", "sinking") | Out-Null
    $excel.Run("Harness_ClearSchedule", "FIP_CallSchedule") | Out-Null
    $excel.Run("Harness_SetSchedule", "FIP_SinkingSchedule", `
               "2011-04-01|0.25|100;2012-04-01|0.25|100") | Out-Null
    $excel.Run("Harness_SetText", "FIP_SinkingFractionBasis", "outstanding") | Out-Null
    $req6 = Get-Request (Join-Path $temp "ryse_sinking_request.json")
    Check "sinking row serialised in full" `
        (($req6.bond.sinking_schedule[0].date -eq "2011-04-01") -and `
         ($req6.bond.sinking_schedule[0].fraction -eq 0.25) -and `
         ($req6.bond.sinking_schedule[0].price_per_100 -eq 100)) `
        "date / fraction of OUTSTANDING / price per 100"
    Check "sinking basis transmitted, never defaulted" `
        ($req6.bond.sinking_fraction_basis -eq "outstanding") `
        "bond.sinking_fraction_basis = $($req6.bond.sinking_fraction_basis)"

    # --- 4.6 response mapping, from the committed fixtures ------------------------------
    # These run in BOTH modes: they need no engine, only the response the engine produced.
    $excel.Run("Harness_Populate", (Join-Path $examples "callable_calibrate_response_v1_1.json")) | Out-Null
    $cOas = $excel.Run("Harness_Get", "FIP_ImpliedOASBp")
    $cDur = $excel.Run("Harness_Get", "FIP_EffectiveDuration")
    Check "callable response mapped" `
        ((Near $cOas 635.7847879698965 1e-6) -and (Near $cDur 2.1477821341758556 1e-9)) `
        "OAS $cOas bp, duration $cDur y"
    $cEngine = $excel.Run("Harness_Get", "FIP_Engine")
    $cType = $excel.Run("Harness_Get", "FIP_InstrumentTypeUsed")
    $cVol = $excel.Run("Harness_Get", "FIP_VolatilityUsed")
    Check "engine, type and volatility echoed" `
        (($cEngine -eq "corporate_callable") -and ($cType -eq "callable") -and (Near $cVol 0.15 1e-12)) `
        "$cEngine / $cType / vol $cVol"
    $cVolNote = $excel.Run("Harness_Get", "FIP_VolatilityApplicability")
    Check "volatility reported as USED for a tree product" ($cVolNote -like "used*") `
        "$($cVolNote.Substring(0, [math]::Min(58, $cVolNote.Length)))..."

    $excel.Run("Harness_Populate", (Join-Path $examples "puttable_response_v1_1.json")) | Out-Null
    $pOas = $excel.Run("Harness_Get", "FIP_ImpliedOASBp")
    Check "puttable response mapped (synthetic fixture)" (Near $pOas 524.0332691173533 1e-6) `
        "OAS $pOas bp - a SYNTHETIC bond; no URS holding is puttable"

    $excel.Run("Harness_Populate", (Join-Path $examples "sinking_response_v1_1.json")) | Out-Null
    $sOas = $excel.Run("Harness_Get", "FIP_ImpliedOASBp")
    Check "sinking response mapped (synthetic fixture)" (Near $sOas 666.895386209944 1e-6) `
        "OAS $sOas bp - a SYNTHETIC bond; no URS holding is a sinking fund"

    # --- 4.7 the three structured refusals, and stale cells ----------------------------
    $excel.Run("Harness_Populate", (Join-Path $examples "call_put_conflict_response_v1_1.json")) | Out-Null
    $e1 = $excel.Run("Harness_Get", "FIP_Errors")
    $c1 = $excel.Run("Harness_Get", "FIP_ModelCleanPrice")
    Check "contradictory call/put shown as a schedule error" `
        (($e1 -like "VALIDATION_ERROR*") -and ($e1 -like "*put price*") -and `
         ([string]::IsNullOrEmpty($c1))) `
        "named the schedule, not the price; stale numbers cleared"

    $excel.Run("Harness_Populate", (Join-Path $examples "sinking_original_basis_response_v1_1.json")) | Out-Null
    $e2 = $excel.Run("Harness_Get", "FIP_Errors")
    Check "original-face sinking basis refused with its reason" `
        (($e2 -like "VALIDATION_ERROR*") -and ($e2 -like "*sub-bond*")) `
        "$($e2.Substring(0, [math]::Min(58, $e2.Length)))..."

    $excel.Run("Harness_Populate", (Join-Path $examples "call_not_representable_response_v1_1.json")) | Out-Null
    $e3 = $excel.Run("Harness_Get", "FIP_Errors")
    $c3 = $excel.Run("Harness_Get", "FIP_ImpliedOASBp")
    Check "a call the grid cannot place shows the real reason" `
        (($e3 -like "VALIDATION_ERROR*") -and ($e3 -like "*coupon date*") -and `
         ([string]::IsNullOrEmpty($c3))) `
        "the sheet says WHY, and shows no number"

    # --- 4.8 a LIVE typed round trip, only when a real interpreter was named -----------
    if ($PythonExe) {
        $excel.Run("Harness_SetText", "FIP_InstrumentType", "callable") | Out-Null
        $excel.Run("Harness_ClearSchedule", "FIP_SinkingSchedule") | Out-Null
        $excel.Run("Harness_SetText", "FIP_SinkingFractionBasis", "") | Out-Null
        $excel.Run("Harness_SetSchedule", "FIP_CallSchedule", "2011-04-01|100;2012-04-01|100") | Out-Null
        $liveResp = Join-Path $temp "ryse_callable_live_response.json"
        $rc = $excel.Run("Harness_TypedRoundTrip", (Join-Path $temp "ryse_callable_live_request.json"), $liveResp)
        $lOas = $excel.Run("Harness_Get", "FIP_ImpliedOASBp")
        Check "LIVE callable round trip through Python" `
            (($rc -eq 0) -and (Near $lOas 635.7847879698965 1e-6)) `
            "exit $rc, OAS $lOas bp - equals the endpoint and the direct wrapper call"

        # the two volatility experiments, as three ordinary single-bond calls
        $prices = @()
        foreach ($vol in @("0.10", "0.15", "0.20")) {
            $excel.Run("Harness_SetNumber", "FIP_YieldVolatility", $vol) | Out-Null
            $excel.Run("Harness_TypedRoundTrip", (Join-Path $temp "ryse_vol_req.json"), `
                       (Join-Path $temp "ryse_vol_resp.json")) | Out-Null
            $prices += [double]($excel.Run("Harness_Get", "FIP_ImpliedOASBp"))
        }
        Check "volatility direction holds from Excel" `
            (($prices[0] -gt $prices[1]) -and ($prices[1] -gt $prices[2])) `
            "OAS tightens as volatility rises: $([math]::Round($prices[0],2)) > $([math]::Round($prices[1],2)) > $([math]::Round($prices[2],2)) bp"
        $excel.Run("Harness_SetNumber", "FIP_YieldVolatility", "0.15") | Out-Null
    }

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
