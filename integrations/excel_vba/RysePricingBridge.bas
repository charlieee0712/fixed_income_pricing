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
' Entry points (all preserved from v1; PriceVanillaBond is now a wrapper):
'   PriceBond                   the button: sheet -> engine -> sheet, any instrument type
'   PriceVanillaBond            the v1 name, kept working — calls PriceBond
'   WriteRequestToFile          write the request JSON only (inspect what Excel sends)
'   PopulateFromResponseFile    map a saved response into the sheet (fixture smoke test,
'                               works with no Python installed at all)
'
' Instrument types (2026-08-31). The bond's type travels IN the request, so one sheet and
' one code path reach every product the engine supports. A sheet that names no type sends
' EXACTLY the v1.0 vanilla request it always did — that is what keeps the existing
' workbook, and its 23 checks, working untouched.
'
'   FIP_InstrumentType   vanilla | stepped | floating | fixed_to_floating |
'                        callable | puttable | sinking      (absent -> vanilla)
'   FIP_Operation        calibrate_and_risk | price_at_oas  (absent -> calibrate_and_risk)
'   FIP_OASBp            read ONLY for price_at_oas: the calibrating operation refuses a
'                        supplied spread, so sending one would turn a good sheet into an error
'   FIP_SinkingFractionBasis   "outstanding" — never defaulted here
'
' Floating-rate inputs (2026-08-31), read ONLY when the type is "floating":
'
'   FIP_QuotedMarginBp    the contractual margin over the index, in basis points. Leave it
'                         blank and the calibrated spread ABSORBS the margin as well as the
'                         credit, which the response says out loud (UNUSED_FIELD) — the price
'                         is still exact, but the spread is then a discount margin.
'   FIP_CurrentCouponPct  the coupon already fixed at the last reset, in percent. Leave it
'                         blank and it is estimated from the curve and frozen through the
'                         risk bumps, which the response also says out loud
'                         (PROVISIONAL_RISK): the price is unaffected, the sensitivities
'                         are provisional.
'
' Both are OPTIONAL and neither is defaulted silently. `fixed_to_floating` needs a switch
' date as well and has no cell for one, so it remains unconstructible from a sheet on
' purpose: the worksheet layout is Mario's decision, not this module's.
'
' Exercise schedules are named Excel TABLES, so they can be any length and can sit
' anywhere on any sheet:
'
'   FIP_CallSchedule      Date | PricePer100
'   FIP_PutSchedule       Date | PricePer100
'   FIP_SinkingSchedule   Date | FractionOutstanding | PricePer100
'
' The rule for all three: a wholly blank row is ignored, a PARTLY filled row is an error
' naming the table and the row, dates become ISO strings, and nothing is sorted, deduped,
' inferred or defaulted. An assumed exercise price or redemption fraction would be a
' contractual term nobody agreed to.
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

' Instrument-type / operation inputs. ALL OPTIONAL: absent means the v1.0 vanilla path.
Private Const NAME_INSTRUMENT_TYPE As String = "FIP_InstrumentType"
Private Const NAME_OPERATION As String = "FIP_Operation"
Private Const NAME_OAS_BP As String = "FIP_OASBp"
Private Const NAME_SINK_BASIS As String = "FIP_SinkingFractionBasis"
Private Const NAME_QUOTED_MARGIN As String = "FIP_QuotedMarginBp"
Private Const NAME_CURRENT_COUPON As String = "FIP_CurrentCouponPct"

' Named Excel Tables (ListObjects) holding variable-length exercise schedules.
Private Const TABLE_CALL As String = "FIP_CallSchedule"
Private Const TABLE_PUT As String = "FIP_PutSchedule"
Private Const TABLE_SINK As String = "FIP_SinkingSchedule"

Private Const OP_CALIBRATE As String = "calibrate_and_risk"
Private Const OP_PRICE_AT_OAS As String = "price_at_oas"

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

' Optional extra outputs — useful on an engineering/QA surface, ignored if the sheet
' does not define them.
Private Const OUT_ENGINE As String = "FIP_Engine"
Private Const OUT_TYPE_USED As String = "FIP_InstrumentTypeUsed"
Private Const OUT_VOL_USED As String = "FIP_VolatilityUsed"


'------------------------------------------------------------------ the button
Public Sub PriceVanillaBond()
    ' The v1 entry point, kept so existing buttons and macros keep working. It is now a
    ' wrapper: a sheet that names no instrument type still sends the same vanilla request.
    PriceBond
End Sub

Public Sub PriceBond()
    ' Sheet -> request JSON -> runner -> response JSON -> sheet. One click, any type.
    Dim requestPath As String, responsePath As String
    Dim exitCode As Long
    Dim response As Object

    On Error GoTo Failed

    requestPath = TempFilePath("ryse_request_")
    responsePath = TempFilePath("ryse_response_")

    WriteRequestJson BuildRequest(), requestPath
    exitCode = RunPricingCommand(requestPath, responsePath)

    If Not FileExists(responsePath) Then
        ' Exit code 2 (or a broken runner): the process never produced an answer.
        ReportFailure "The pricing runner did not produce a response file " & _
                      "(exit code " & exitCode & "). Check " & NAME_RUNNER & "."
        Exit Sub
    End If

    Set response = ReadResponseJson(responsePath)
    PopulateOutputs response

    DeleteFileIfPresent requestPath
    DeleteFileIfPresent responsePath
    Exit Sub

Failed:
    ReportFailure "Bridge error " & Err.Number & ": " & Err.Description
End Sub


'------------------------------------------------------------------ build the request
Public Function BuildVanillaRequest() As Object
    ' The v1 name, kept working. A sheet with no FIP_InstrumentType produces exactly the
    ' request it always did.
    Set BuildVanillaRequest = BuildRequest()
End Function

Public Function BuildRequest() As Object
    ' Read the named input cells and return the request as nested Dictionaries.
    ' Optional cells left empty are OMITTED so the engine applies its own defaults.
    Dim request As Object, bond As Object, market As Object
    Dim analysis As Object, model As Object, metadata As Object
    Dim instrumentType As String, operation As String

    Set request = New Dictionary
    Set bond = New Dictionary
    Set market = New Dictionary
    Set analysis = New Dictionary
    Set model = New Dictionary
    Set metadata = New Dictionary

    instrumentType = LCase$(Trim$(OptionalText(NAME_INSTRUMENT_TYPE)))
    operation = LCase$(Trim$(OptionalText(NAME_OPERATION)))
    If Len(operation) = 0 Then operation = OP_CALIBRATE

    If Len(instrumentType) = 0 Then
        request("schema_version") = "1.0"          ' the untouched v1.0 path
    Else
        request("schema_version") = "1.1"
        bond("instrument_type") = instrumentType
    End If
    request("request_id") = "XL-" & Format$(Now, "yyyymmdd-hhnnss")
    request("operation") = operation

    If HasValue(NAME_INSTRUMENT) Then bond("instrument_id") = CStr(NamedValue(NAME_INSTRUMENT))
    bond("currency") = UCase$(Trim$(CStr(NamedValue(NAME_CURRENCY))))
    If HasValue(NAME_COUPON) Then bond("coupon_pct") = CDbl(NamedValue(NAME_COUPON))
    bond("coupon_frequency") = CLng(NamedValue(NAME_FREQUENCY))
    ' ISO STRINGS, never Excel serial numbers: the engine refuses a numeric date
    ' because a serial would silently be read as 1970-01-01.
    bond("maturity_date") = IsoDate(NamedValue(NAME_MATURITY))

    AddExerciseSchedules bond, instrumentType
    AddFloatingTerms bond, instrumentType

    market("valuation_date") = IsoDate(NamedValue(NAME_VALUATION))
    If HasValue(NAME_CLEAN_PRICE) Then
        market("clean_price_per_100") = CDbl(NamedValue(NAME_CLEAN_PRICE))
    End If

    If HasValue(NAME_SHIFT) Then analysis("spread_shift_bp") = CDbl(NamedValue(NAME_SHIFT))
    If operation = OP_PRICE_AT_OAS Then
        ' Read ONLY here. calibrate_and_risk REFUSES a supplied spread, because a mark and
        ' a typed spread can disagree and there is no principled way to choose; sending one
        ' anyway would turn a perfectly good sheet into an error response.
        If HasValue(NAME_OAS_BP) Then analysis("oas_bp") = CDbl(NamedValue(NAME_OAS_BP))
    End If
    If HasValue(NAME_VOLATILITY) Then
        ' The option-free types do not use this. It is sent anyway so the response can say
        ' so explicitly instead of the sheet quietly implying it mattered.
        model("yield_volatility_decimal") = CDbl(NamedValue(NAME_VOLATILITY))
    End If

    metadata("source") = "excel_bridge"
    metadata("workbook") = ThisWorkbook.Name

    Set request("bond") = bond
    Set request("market") = market
    If analysis.Count > 0 Then Set request("analysis") = analysis
    If model.Count > 0 Then Set request("model") = model
    Set request("metadata") = metadata

    Set BuildRequest = request
End Function


'------------------------------------------------------------------ exercise schedules
Private Sub AddExerciseSchedules(ByVal bond As Object, ByVal instrumentType As String)
    ' Only the tree products carry exercise rights. For every other type the tables are
    ' not read at all, so a workbook may keep them lying around without affecting a
    ' vanilla or floating request.
    Select Case instrumentType
        Case "callable", "puttable", "sinking"
            AddSchedule bond, "call_schedule", TABLE_CALL, False
            AddSchedule bond, "put_schedule", TABLE_PUT, False
            AddSchedule bond, "sinking_schedule", TABLE_SINK, True
            If HasValue(NAME_SINK_BASIS) Then
                ' Never defaulted here. The engine requires it with a sinking schedule and
                ' names the field if it is missing; guessing "outstanding" would hide a
                ' caller who actually meant fractions of the ORIGINAL face.
                bond("sinking_fraction_basis") = Trim$(CStr(NamedValue(NAME_SINK_BASIS)))
            End If
    End Select
End Sub

Private Sub AddFloatingTerms(ByVal bond As Object, ByVal instrumentType As String)
    ' The two terms only a floating-rate note has. Both OPTIONAL, neither defaulted: the
    ' engine reports what it did without either, and a guessed margin or a guessed reset
    ' would be a contractual term nobody agreed to — the same rule the schedules follow.
    '
    ' Gated on "floating" alone, deliberately. `fixed_to_floating` uses the margin too, but
    ' it also needs a switch date, and adding a cell for that would make a SIXTH type
    ' constructible from a sheet whose layout has not been decided. That is Mario's call.
    If instrumentType <> "floating" Then Exit Sub

    If HasValue(NAME_QUOTED_MARGIN) Then
        bond("quoted_margin_bp") = CDbl(NamedValue(NAME_QUOTED_MARGIN))
    End If
    If HasValue(NAME_CURRENT_COUPON) Then
        bond("current_coupon_pct") = CDbl(NamedValue(NAME_CURRENT_COUPON))
    End If
End Sub

Private Sub AddSchedule(ByVal bond As Object, ByVal fieldName As String, _
                        ByVal tableName As String, ByVal wantFraction As Boolean)
    Dim entries As Object
    Set entries = ScheduleRows(tableName, wantFraction)
    ' An absent or empty table is OMITTED, never sent as an empty or invented schedule.
    ' A required one that is missing comes back as the engine's own named refusal.
    If entries Is Nothing Then Exit Sub
    Set bond(fieldName) = entries
End Sub

Private Function ScheduleRows(ByVal tableName As String, ByVal wantFraction As Boolean) As Object
    ' One named Excel Table -> a JSON array of objects, in the table's own row order.
    Dim table As Object, body As Object, entries As Object, entry As Object
    Dim r As Long, filled As Long, expected As Long
    Dim dateCell As Variant, fractionCell As Variant, priceCell As Variant

    Set table = FindTable(tableName)
    If table Is Nothing Then Exit Function
    Set body = table.DataBodyRange
    If body Is Nothing Then Exit Function                  ' header row only

    Set entries = New Collection
    expected = IIf(wantFraction, 3, 2)

    For r = 1 To body.Rows.Count
        dateCell = body.Cells(r, 1).Value
        If wantFraction Then
            fractionCell = body.Cells(r, 2).Value
            priceCell = body.Cells(r, 3).Value
        Else
            fractionCell = Empty
            priceCell = body.Cells(r, 2).Value
        End If

        filled = 0
        If Not IsBlankValue(dateCell) Then filled = filled + 1
        If Not IsBlankValue(priceCell) Then filled = filled + 1
        If wantFraction Then
            If Not IsBlankValue(fractionCell) Then filled = filled + 1
        End If

        If filled > 0 Then
            If filled < expected Then
                Err.Raise vbObjectError + 514, "RysePricingBridge", _
                    "Table " & tableName & ", row " & r & " is only partly filled (" & _
                    filled & " of " & expected & " values). Fill the whole row or clear " & _
                    "it. Nothing is defaulted here: an assumed exercise price or " & _
                    "redemption fraction would be a contractual term nobody agreed to."
            End If
            Set entry = New Dictionary
            ' ISO string, never an Excel serial - a serial would be read as 1970-01-01.
            entry("date") = IsoDate(dateCell)
            If wantFraction Then entry("fraction") = CDbl(fractionCell)
            entry("price_per_100") = CDbl(priceCell)
            entries.Add entry                              ' row ORDER preserved
        End If
    Next r

    If entries.Count = 0 Then Exit Function                ' all rows blank -> omitted
    Set ScheduleRows = entries
End Function

Private Function FindTable(ByVal tableName As String) As Object
    ' Workbook-wide lookup, so a schedule table can live on any sheet. This is what keeps
    ' the bridge independent of the final worksheet layout, which is Mario's to choose.
    Dim sheet As Object, table As Object
    For Each sheet In ThisWorkbook.Worksheets
        For Each table In sheet.ListObjects
            If StrComp(table.Name, tableName, vbTextCompare) = 0 Then
                Set FindTable = table
                Exit Function
            End If
        Next table
    Next sheet
End Function

Private Function IsBlankValue(ByVal Value As Variant) As Boolean
    If IsEmpty(Value) Then IsBlankValue = True: Exit Function
    If IsNull(Value) Then IsBlankValue = True: Exit Function
    IsBlankValue = (Len(Trim$(CStr(Value))) = 0)
End Function

Private Function OptionalText(ByVal cellName As String) As String
    If HasValue(cellName) Then OptionalText = CStr(NamedValue(cellName))
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
    ' The v1 name, kept working.
    PopulateOutputs response
End Sub

Public Sub PopulateOutputs(ByVal response As Object)
    ' Map one response onto the named output cells. Missing names are skipped, so a
    ' sheet may show only the outputs it cares about. The result fields below are the
    ' ones EVERY instrument type returns; a product's extras (next reset, next switch,
    ' the volatility numbers) are in the response JSON and on the QA surface, not in a
    ' type-specific panel — that panel is Mario's layout decision, not ours.
    Dim results As Object

    SetNamedValue OUT_STATUS, Field(response, "status")
    SetNamedValue OUT_WARNINGS, JoinMessages(Field(response, "warnings"))
    SetNamedValue OUT_ERRORS, JoinMessages(Field(response, "errors"))
    SetNamedValue OUT_VOL_NOTE, VolatilityNote(response)

    If Field(response, "status") <> "ok" Then
        ClearResultCells
        Exit Sub
    End If

    Set results = FieldObject(response, "results")
    If results Is Nothing Then Exit Sub
    SetNamedValue OUT_CLEAN, Field(results, "model_clean_price_per_100")
    SetNamedValue OUT_DIRTY, Field(results, "model_dirty_price_per_100")
    SetNamedValue OUT_ACCRUED, Field(results, "accrued_interest_per_100")
    SetNamedValue OUT_OAS, Field(results, "implied_oas_bp")
    SetNamedValue OUT_DURATION, Field(results, "effective_duration_years")
    SetNamedValue OUT_DV01, Field(results, "dv01_per_100")
    SetNamedValue OUT_CONVEXITY, Field(results, "convexity")
    SetNamedValue OUT_TIGHTER, Field(results, "price_spread_tighter_per_100")
    SetNamedValue OUT_WIDER, Field(results, "price_spread_wider_per_100")
    SetNamedValue OUT_CURVE, Field(FieldObject(response, "market_data"), "curve_id")

    ' Optional engineering outputs: what the engine says it actually did.
    SetNamedValue OUT_ENGINE, Field(response, "engine")
    SetNamedValue OUT_TYPE_USED, Field(FieldObject(response, "inputs_used"), "instrument_type")
    SetNamedValue OUT_VOL_USED, Field(results, "volatility_used_decimal")
End Sub

Private Function VolatilityNote(ByVal response As Object) As String
    ' The plain-language answer to "did it use my volatility?" — always stated.
    Dim applicability As Object, vol As Object

    ' FieldObject, not Field: on an error response "applicability" is JSON null, which
    ' arrives in VBA as Null (a Variant), and `Set x = Null` raises "Object required".
    Set applicability = FieldObject(response, "applicability")
    If applicability Is Nothing Then Exit Function
    Set vol = FieldObject(applicability, "yield_volatility")
    If vol Is Nothing Then Exit Function

    If Field(vol, "used") = True Then
        ' A tree product: say what it was worth, in both directions, rather than "used".
        VolatilityNote = "used — " & _
            EffectText(Field(vol, "price_effect_per_1pct_vol"), " price / vol point") & _
            EffectText(Field(vol, "oas_effect_bp_per_1pct_vol"), " bp OAS / vol point")
        If Len(Trim$(VolatilityNote)) <= 7 Then VolatilityNote = "used"
    Else
        ' Names the TYPE, so the sentence stays true for every product. For a vanilla
        ' request this is the v1 wording, unchanged.
        VolatilityNote = "not used by " & UsedType(response) & " — " & _
                         CStr(Field(vol, "reason"))
    End If
End Function

Private Function UsedType(ByVal response As Object) As String
    ' The instrument type the engine echoed back; "vanilla" when the caller named none.
    Dim used As Object
    UsedType = "vanilla"
    Set used = FieldObject(response, "inputs_used")
    If used Is Nothing Then Exit Function
    If Not used.Exists("instrument_type") Then Exit Function
    If IsNull(used("instrument_type")) Then Exit Function
    UsedType = CStr(used("instrument_type"))
End Function

Private Function EffectText(ByVal value As Variant, ByVal suffix As String) As String
    ' A null volatility effect is left out entirely rather than shown as zero.
    If IsNull(value) Or IsEmpty(value) Then Exit Function
    If Not IsNumeric(value) Then Exit Function
    EffectText = Format$(CDbl(value), "0.0000") & suffix & "; "
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
    PopulateOutputs ReadResponseJson(CStr(path))
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

Private Function FieldObject(ByVal container As Object, ByVal key As String) As Object
    ' Like Field, but for values that should be objects (a nested JSON object). Returns
    ' Nothing when the container is Nothing, the key is absent, or the value is JSON
    ' null — the last case being why callers must not use `Set x = Field(...)`.
    If container Is Nothing Then Exit Function
    If Not container.Exists(key) Then Exit Function
    If Not IsObject(container(key)) Then Exit Function
    Set FieldObject = container(key)
End Function

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

    ' Test IsObject FIRST: `Is Nothing` on a non-object (Empty, or a JSON null) is
    ' itself a type error.
    If Not IsObject(entries) Then Exit Function
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
