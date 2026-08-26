Attribute VB_Name = "RysePricingBridge"
'==========================================================================================
' RYSE fixed-income pricing — Excel bridge (v1, 2026-08-25)
'
' This module is an ADAPTER, nothing more. It reads named cells, writes one request
' JSON, runs one configured command, reads one response JSON, and writes the answers
' back into named cells. It contains NO pricing logic: no curve choice, no OAS, no
' duration, no day-count and no volatility rule lives here. Every number comes from
' the Python engine, which is the same engine the validated production runs use.
'
' Requires:
'   * module JsonConverter (VBA-JSON v2.3.1, vendored beside this file)
'   * Tools > References > "Microsoft Scripting Runtime"   (VBA-JSON uses Dictionary)
'   * one runner command, configured as described in README.md — NOT hard-coded here
'
' Entry points:
'   PriceVanillaBond            the button: sheet -> engine -> sheet
'   WriteRequestToFile          write the request JSON only (inspect what Excel sends)
'   PopulateFromResponseFile    map a saved response into the sheet (fixture smoke test,
'                               works with no Python installed at all)
'==========================================================================================
Option Explicit

' Input cells (workbook-level named ranges).
Private Const NAME_INSTRUMENT As String = "FIP_InstrumentId"
Private Const NAME_CURRENCY As String = "FIP_Currency"
Private Const NAME_COUPON As String = "FIP_CouponPct"
Private Const NAME_FREQUENCY As String = "FIP_CouponFrequency"
Private Const NAME_MATURITY As String = "FIP_MaturityDate"
Private Const NAME_VALUATION As String = "FIP_ValuationDate"
Private Const NAME_CLEAN_PRICE As String = "FIP_CleanMarketPrice"
Private Const NAME_SHIFT As String = "FIP_SpreadShiftBp"
Private Const NAME_VOLATILITY As String = "FIP_YieldVolatility"
Private Const NAME_RUNNER As String = "FIP_RunnerCommand"

' Output cells.
Private Const OUT_STATUS As String = "FIP_Status"
Private Const OUT_CLEAN As String = "FIP_ModelCleanPrice"
Private Const OUT_DIRTY As String = "FIP_ModelDirtyPrice"
Private Const OUT_ACCRUED As String = "FIP_AccruedInterest"
Private Const OUT_OAS As String = "FIP_ImpliedOASBp"
Private Const OUT_DURATION As String = "FIP_EffectiveDuration"
Private Const OUT_DV01 As String = "FIP_DV01"
Private Const OUT_CONVEXITY As String = "FIP_Convexity"
Private Const OUT_TIGHTER As String = "FIP_TighterPrice"
Private Const OUT_WIDER As String = "FIP_WiderPrice"
Private Const OUT_CURVE As String = "FIP_CurveId"
Private Const OUT_VOL_NOTE As String = "FIP_VolatilityApplicability"
Private Const OUT_WARNINGS As String = "FIP_Warnings"
Private Const OUT_ERRORS As String = "FIP_Errors"


'------------------------------------------------------------------ the button
Public Sub PriceVanillaBond()
    ' Sheet -> request JSON -> runner -> response JSON -> sheet. One click.
    Dim requestPath As String, responsePath As String
    Dim exitCode As Long
    Dim response As Object

    On Error GoTo Failed

    requestPath = TempFilePath("ryse_request_")
    responsePath = TempFilePath("ryse_response_")

    WriteRequestJson BuildVanillaRequest(), requestPath
    exitCode = RunPricingCommand(requestPath, responsePath)

    If Not FileExists(responsePath) Then
        ' Exit code 2 (or a broken runner): the process never produced an answer.
        ReportFailure "The pricing runner did not produce a response file " & _
                      "(exit code " & exitCode & "). Check " & NAME_RUNNER & "."
        Exit Sub
    End If

    Set response = ReadResponseJson(responsePath)
    PopulateVanillaOutputs response

    DeleteFileIfPresent requestPath
    DeleteFileIfPresent responsePath
    Exit Sub

Failed:
    ReportFailure "Bridge error " & Err.Number & ": " & Err.Description
End Sub


'------------------------------------------------------------------ build the request
Public Function BuildVanillaRequest() As Object
    ' Read the named input cells and return the request as nested Dictionaries.
    ' Optional cells left empty are OMITTED so the engine applies its own defaults.
    Dim request As Object, bond As Object, market As Object
    Dim analysis As Object, model As Object, metadata As Object

    Set request = New Dictionary
    Set bond = New Dictionary
    Set market = New Dictionary
    Set analysis = New Dictionary
    Set model = New Dictionary
    Set metadata = New Dictionary

    request("schema_version") = "1.0"
    request("request_id") = "XL-" & Format$(Now, "yyyymmdd-hhnnss")
    request("operation") = "calibrate_and_risk"

    If HasValue(NAME_INSTRUMENT) Then bond("instrument_id") = CStr(NamedValue(NAME_INSTRUMENT))
    bond("currency") = UCase$(Trim$(CStr(NamedValue(NAME_CURRENCY))))
    bond("coupon_pct") = CDbl(NamedValue(NAME_COUPON))
    bond("coupon_frequency") = CLng(NamedValue(NAME_FREQUENCY))
    ' ISO STRINGS, never Excel serial numbers: the engine refuses a numeric date
    ' because a serial would silently be read as 1970-01-01.
    bond("maturity_date") = IsoDate(NamedValue(NAME_MATURITY))

    market("valuation_date") = IsoDate(NamedValue(NAME_VALUATION))
    market("clean_price_per_100") = CDbl(NamedValue(NAME_CLEAN_PRICE))

    If HasValue(NAME_SHIFT) Then analysis("spread_shift_bp") = CDbl(NamedValue(NAME_SHIFT))
    If HasValue(NAME_VOLATILITY) Then
        ' Vanilla does not use this. It is sent anyway so the response can say so
        ' explicitly instead of the sheet quietly implying it mattered.
        model("yield_volatility_decimal") = CDbl(NamedValue(NAME_VOLATILITY))
    End If

    metadata("source") = "excel_bridge"
    metadata("workbook") = ThisWorkbook.Name

    Set request("bond") = bond
    Set request("market") = market
    If analysis.Count > 0 Then Set request("analysis") = analysis
    If model.Count > 0 Then Set request("model") = model
    Set request("metadata") = metadata

    Set BuildVanillaRequest = request
End Function


'------------------------------------------------------------------ files and process
Public Sub WriteRequestJson(ByVal request As Object, ByVal path As String)
    ' Serialise the request and write it as UTF-8 (the engine reads utf-8-sig, so the
    ' byte-order mark Windows adds is harmless).
    WriteTextFile path, JsonConverter.ConvertToJson(request, Whitespace:=2)
End Sub

Public Function RunPricingCommand(ByVal requestPath As String, _
                                  ByVal responsePath As String) As Long
    ' Run the configured command and WAIT for it (waitOnReturn:=True). The workbook
    ' never learns what the runner is: local Python, a packaged executable or an HTTP
    ' client wrapper are all the same one-line setting.
    Dim shell As Object, command As String

    command = RunnerCommand() & _
              " --input """ & requestPath & """" & _
              " --output """ & responsePath & """"

    Set shell = CreateObject("WScript.Shell")
    RunPricingCommand = shell.Run(command, 0, True)      ' 0 = no window, True = wait
End Function

Public Function ReadResponseJson(ByVal path As String) As Object
    Set ReadResponseJson = JsonConverter.ParseJson(ReadTextFile(path))
End Function


'------------------------------------------------------------------ write results back
Public Sub PopulateVanillaOutputs(ByVal response As Object)
    ' Map one response onto the named output cells. Missing names are skipped, so a
    ' sheet may show only the outputs it cares about.
    Dim results As Object

    SetNamedValue OUT_STATUS, Field(response, "status")
    SetNamedValue OUT_WARNINGS, JoinMessages(Field(response, "warnings"))
    SetNamedValue OUT_ERRORS, JoinMessages(Field(response, "errors"))
    SetNamedValue OUT_VOL_NOTE, VolatilityNote(response)

    If Field(response, "status") <> "ok" Then
        ClearResultCells
        Exit Sub
    End If

    Set results = Field(response, "results")
    SetNamedValue OUT_CLEAN, Field(results, "model_clean_price_per_100")
    SetNamedValue OUT_DIRTY, Field(results, "model_dirty_price_per_100")
    SetNamedValue OUT_ACCRUED, Field(results, "accrued_interest_per_100")
    SetNamedValue OUT_OAS, Field(results, "implied_oas_bp")
    SetNamedValue OUT_DURATION, Field(results, "effective_duration_years")
    SetNamedValue OUT_DV01, Field(results, "dv01_per_100")
    SetNamedValue OUT_CONVEXITY, Field(results, "convexity")
    SetNamedValue OUT_TIGHTER, Field(results, "price_spread_tighter_per_100")
    SetNamedValue OUT_WIDER, Field(results, "price_spread_wider_per_100")
    SetNamedValue OUT_CURVE, Field(Field(response, "market_data"), "curve_id")
End Sub

Private Function VolatilityNote(ByVal response As Object) As String
    ' The plain-language answer to "did it use my volatility?" — always stated.
    Dim applicability As Object, vol As Object

    Set applicability = Field(response, "applicability")
    If applicability Is Nothing Then Exit Function
    Set vol = Field(applicability, "yield_volatility")
    If vol Is Nothing Then Exit Function

    If Field(vol, "used") = True Then
        VolatilityNote = "used"
    Else
        VolatilityNote = "not used by vanilla — " & CStr(Field(vol, "reason"))
    End If
End Function

Private Sub ClearResultCells()
    Dim cellName As Variant
    For Each cellName In Array(OUT_CLEAN, OUT_DIRTY, OUT_ACCRUED, OUT_OAS, OUT_DURATION, _
                               OUT_DV01, OUT_CONVEXITY, OUT_TIGHTER, OUT_WIDER, OUT_CURVE)
        SetNamedValue CStr(cellName), ""
    Next cellName
End Sub


'------------------------------------------------------------------ manual helpers
Public Sub WriteRequestToFile()
    ' Inspect exactly what this sheet would send, without running anything.
    Dim path As String
    path = TempFilePath("ryse_request_")
    WriteRequestJson BuildVanillaRequest(), path
    MsgBox "Request written to:" & vbCrLf & path, vbInformation, "RYSE pricing bridge"
End Sub

Public Sub PopulateFromResponseFile()
    ' Fixture smoke test: map a saved response (e.g. the committed
    ' examples\vanilla_response_v1.json) into the sheet. No Python required.
    Dim path As Variant
    path = Application.GetOpenFilename("JSON files (*.json), *.json", , _
                                       "Choose a saved response JSON")
    If VarType(path) = vbBoolean Then Exit Sub
    PopulateVanillaOutputs ReadResponseJson(CStr(path))
End Sub


'------------------------------------------------------------------ small utilities
Private Function RunnerCommand() As String
    ' Where the engine lives — a workbook setting, else an environment variable.
    ' Never a hard-coded path, never a server name, never an SSH command.
    Dim command As String

    If HasValue(NAME_RUNNER) Then command = Trim$(CStr(NamedValue(NAME_RUNNER)))
    If Len(command) = 0 Then command = Trim$(Environ$("FIP_RUNNER_COMMAND"))
    If Len(command) = 0 Then
        Err.Raise vbObjectError + 513, "RysePricingBridge", _
            "No pricing runner is configured. Set the named cell " & NAME_RUNNER & _
            " (or the FIP_RUNNER_COMMAND environment variable) to the command that " & _
            "accepts --input and --output. See README.md."
    End If
    RunnerCommand = command
End Function

Private Function IsoDate(ByVal value As Variant) As String
    ' Excel dates are numbers; the engine demands ISO strings. This is that conversion.
    If IsDate(value) Then
        IsoDate = Format$(CDate(value), "yyyy-mm-dd")
    Else
        IsoDate = Trim$(CStr(value))
    End If
End Function

Private Function NamedValue(ByVal cellName As String) As Variant
    NamedValue = ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).value
End Function

Private Function HasName(ByVal cellName As String) As Boolean
    Dim ignored As Object
    On Error Resume Next
    Set ignored = ThisWorkbook.Names(cellName)
    HasName = (Err.Number = 0)
    On Error GoTo 0
End Function

Private Function HasValue(ByVal cellName As String) As Boolean
    ' True when the name exists and its cell is not blank.
    If Not HasName(cellName) Then Exit Function
    HasValue = Len(Trim$(CStr(NamedValue(cellName)))) > 0
End Function

Private Sub SetNamedValue(ByVal cellName As String, ByVal value As Variant)
    If Not HasName(cellName) Then Exit Sub           ' the sheet may not show this output
    If IsNull(value) Or IsEmpty(value) Then
        ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).value = ""
    Else
        ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).value = value
    End If
End Sub

Private Function Field(ByVal container As Object, ByVal key As String) As Variant
    ' Dictionary lookup that does NOT create the key when it is missing, and returns
    ' objects with Set. JSON null arrives as VBA Null.
    If container Is Nothing Then Exit Function
    If Not container.Exists(key) Then Exit Function
    If IsObject(container(key)) Then
        Set Field = container(key)
    Else
        Field = container(key)
    End If
End Function

Private Function JoinMessages(ByVal entries As Variant) As String
    ' Flatten a warnings/errors collection into one readable cell.
    Dim entry As Variant, line As String, joined As String

    If IsEmpty(entries) Then Exit Function
    If entries Is Nothing Then Exit Function

    For Each entry In entries
        line = CStr(Field(entry, "code")) & ": " & CStr(Field(entry, "message"))
        If Len(joined) = 0 Then joined = line Else joined = joined & vbLf & line
    Next entry
    JoinMessages = joined
End Function

Private Sub ReportFailure(ByVal message As String)
    SetNamedValue OUT_STATUS, "error"
    SetNamedValue OUT_ERRORS, message
    ClearResultCells
    MsgBox message, vbExclamation, "RYSE pricing bridge"
End Sub

Private Function TempFilePath(ByVal prefix As String) As String
    TempFilePath = Environ$("TEMP") & "\" & prefix & Format$(Now, "yyyymmdd_hhnnss") & _
                   "_" & CStr(Int(Rnd * 100000)) & ".json"
End Function

Private Sub WriteTextFile(ByVal path As String, ByVal text As String)
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2                      ' text
    stream.Charset = "utf-8"
    stream.Open
    stream.WriteText text
    stream.SaveToFile path, 2            ' overwrite
    stream.Close
End Sub

Private Function ReadTextFile(ByVal path As String) As String
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Charset = "utf-8"
    stream.Open
    stream.LoadFromFile path
    ReadTextFile = stream.ReadText
    stream.Close
End Function

Private Function FileExists(ByVal path As String) As Boolean
    FileExists = (Len(Dir$(path)) > 0)
End Function

Private Sub DeleteFileIfPresent(ByVal path As String)
    On Error Resume Next
    If FileExists(path) Then Kill path
    On Error GoTo 0
End Sub
