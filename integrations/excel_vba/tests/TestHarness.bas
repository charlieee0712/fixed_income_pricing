Attribute VB_Name = "TestHarness"
' Test scaffold for RysePricingBridge.
'
' All cell reading and writing happens HERE, in VBA, for two reasons: it is what the
' real bridge does, and it keeps the automation driver on strings only (the PowerShell
' COM binder caches a property's type from its first use per call site, so a mixed
' string/number sheet is a minefield from outside).
'
' Nothing here calls the bridge's MsgBox paths: a modal dialog in an invisible Excel
' would hang the run.
Option Explicit

Public Sub Harness_Setup(ByVal runnerPath As String)
    ' Lay out one bond exactly as a user would, then name the cells.
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(1)

    ws.Range("A1").Value = "instrument"
    ws.Range("B1").Value = "DEMO-BOND-001"
    ws.Range("A2").Value = "currency"
    ws.Range("B2").Value = "usd"                    ' lower case on purpose
    ws.Range("A3").Value = "coupon %"
    ws.Range("B3").Value = 6.5
    ws.Range("A4").Value = "frequency"
    ws.Range("B4").Value = 2
    ws.Range("A5").Value = "maturity"
    ws.Range("B5").Value = DateSerial(2017, 1, 15)  ' a REAL Excel date (serial 42750)
    ws.Range("A6").Value = "valuation"
    ws.Range("B6").Value = DateSerial(2009, 3, 31)  ' serial 39903 — the 1970 trap
    ws.Range("A7").Value = "clean price"
    ws.Range("B7").Value = 94.25
    ws.Range("A8").Value = "spread shift bp"
    ws.Range("B8").Value = 10
    ws.Range("A9").Value = "yield volatility"
    ws.Range("B9").Value = 0.15
    ws.Range("A10").Value = "runner"
    ws.Range("B10").Value = runnerPath

    AddName "FIP_InstrumentId", ws.Range("B1")
    AddName "FIP_Currency", ws.Range("B2")
    AddName "FIP_CouponPct", ws.Range("B3")
    AddName "FIP_CouponFrequency", ws.Range("B4")
    AddName "FIP_MaturityDate", ws.Range("B5")
    AddName "FIP_ValuationDate", ws.Range("B6")
    AddName "FIP_CleanMarketPrice", ws.Range("B7")
    AddName "FIP_SpreadShiftBp", ws.Range("B8")
    AddName "FIP_YieldVolatility", ws.Range("B9")
    AddName "FIP_RunnerCommand", ws.Range("B10")

    AddName "FIP_Status", ws.Range("E1")
    AddName "FIP_ModelCleanPrice", ws.Range("E2")
    AddName "FIP_ModelDirtyPrice", ws.Range("E3")
    AddName "FIP_AccruedInterest", ws.Range("E4")
    AddName "FIP_ImpliedOASBp", ws.Range("E5")
    AddName "FIP_EffectiveDuration", ws.Range("E6")
    AddName "FIP_DV01", ws.Range("E7")
    AddName "FIP_Convexity", ws.Range("E8")
    AddName "FIP_TighterPrice", ws.Range("E9")
    AddName "FIP_WiderPrice", ws.Range("E10")
    AddName "FIP_CurveId", ws.Range("E11")
    AddName "FIP_VolatilityApplicability", ws.Range("E12")
    AddName "FIP_Warnings", ws.Range("E13")
    AddName "FIP_Errors", ws.Range("E14")
End Sub

Private Sub AddName(ByVal cellName As String, ByVal target As Range)
    ThisWorkbook.Names.Add Name:=cellName, RefersTo:=target
End Sub

Public Function Harness_Get(ByVal cellName As String) As String
    ' One output cell as text; "" when blank. The comma->dot replace keeps the value
    ' parseable whatever the machine's decimal separator is.
    Dim v As Variant
    v = ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).Value
    If IsEmpty(v) Or IsNull(v) Then
        Harness_Get = ""
    Else
        Harness_Get = Replace(CStr(v), ",", ".")
    End If
End Function

Public Sub Harness_WriteRequest(ByVal path As String)
    WriteRequestJson BuildVanillaRequest(), path
End Sub

Public Sub Harness_Populate(ByVal path As String)
    PopulateVanillaOutputs ReadResponseJson(path)
End Sub

Public Function Harness_RoundTrip(ByVal requestPath As String, _
                                  ByVal responsePath As String) As Long
    ' The whole adapter path minus the MsgBox reporting: cells -> JSON -> command
    ' (waited on) -> response -> cells.
    WriteRequestJson BuildVanillaRequest(), requestPath
    Harness_RoundTrip = RunPricingCommand(requestPath, responsePath)
    PopulateVanillaOutputs ReadResponseJson(responsePath)
End Function

'==========================================================================================
' Instrument-type extension (2026-08-31). Everything above is untouched, so the original
' 23 checks exercise exactly the code path they always did.
'
' The schedule tables are laid out with SIX data rows each and only the first few filled,
' which is deliberate: it exercises "a wholly blank row is ignored" on every run rather
' than only in the test that asks for it.
'==========================================================================================

Public Sub Harness_SetupTypes()
    ' The optional inputs a typed request uses, plus the three schedule tables.
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(1)

    ws.Range("A12").Value = "instrument type"
    ws.Range("A13").Value = "operation"
    ws.Range("A14").Value = "oas bp"
    ws.Range("A15").Value = "sinking basis"
    AddName "FIP_InstrumentType", ws.Range("B12")
    AddName "FIP_Operation", ws.Range("B13")
    AddName "FIP_OASBp", ws.Range("B14")
    AddName "FIP_SinkingFractionBasis", ws.Range("B15")

    ' Extra engineering outputs.
    AddName "FIP_Engine", ws.Range("E15")
    AddName "FIP_InstrumentTypeUsed", ws.Range("E16")
    AddName "FIP_VolatilityUsed", ws.Range("E17")

    MakeTable ws, "FIP_CallSchedule", ws.Range("H1"), Array("Date", "PricePer100")
    MakeTable ws, "FIP_PutSchedule", ws.Range("K1"), Array("Date", "PricePer100")
    MakeTable ws, "FIP_SinkingSchedule", ws.Range("N1"), _
              Array("Date", "FractionOutstanding", "PricePer100")
End Sub

Private Sub MakeTable(ByVal ws As Worksheet, ByVal tableName As String, _
                      ByVal topLeft As Range, ByVal headers As Variant)
    ' A named Excel Table with a header row and six empty data rows.
    Dim c As Long, body As Range, table As ListObject
    For c = 0 To UBound(headers)
        topLeft.Offset(0, c).Value = headers(c)
    Next c
    Set body = ws.Range(topLeft, topLeft.Offset(6, UBound(headers)))
    Set table = ws.ListObjects.Add(xlSrcRange, body, , xlYes)
    table.Name = tableName
End Sub

Public Sub Harness_ClearSchedule(ByVal tableName As String)
    Dim table As ListObject
    Set table = ThisWorkbook.Worksheets(1).ListObjects(tableName)
    If Not table.DataBodyRange Is Nothing Then table.DataBodyRange.ClearContents
End Sub

Public Sub Harness_SetSchedule(ByVal tableName As String, ByVal rows As String)
    ' rows = "2011-04-01|100 ; 2012-04-01|100"  (or "date|fraction|price" for sinking).
    ' Dates are written as REAL Excel dates, so the ISO conversion is genuinely tested.
    Dim table As ListObject, parts As Variant, cells As Variant
    Dim r As Long, c As Long, text As String

    Harness_ClearSchedule tableName
    If Len(Trim$(rows)) = 0 Then Exit Sub

    Set table = ThisWorkbook.Worksheets(1).ListObjects(tableName)
    parts = Split(rows, ";")
    For r = 0 To UBound(parts)
        cells = Split(Trim$(CStr(parts(r))), "|")
        For c = 0 To UBound(cells)
            text = Trim$(CStr(cells(c)))
            If Len(text) = 0 Then
                table.DataBodyRange.Cells(r + 1, c + 1).ClearContents
            ElseIf c = 0 Then
                table.DataBodyRange.Cells(r + 1, c + 1).Value = _
                    DateSerial(CLng(Left$(text, 4)), CLng(Mid$(text, 6, 2)), CLng(Right$(text, 2)))
            Else
                table.DataBodyRange.Cells(r + 1, c + 1).Value = CDbl(text)
            End If
        Next c
    Next r
End Sub

Public Sub Harness_SetText(ByVal cellName As String, ByVal Value As String)
    ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).Value = Value
End Sub

Public Sub Harness_SetDate(ByVal cellName As String, ByVal isoDate As String)
    ' Written as a REAL Excel date, so the bridge's serial-to-ISO conversion is exercised
    ' on every typed test too, not only on the original vanilla one.
    ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).Value = _
        DateSerial(CLng(Left$(isoDate, 4)), CLng(Mid$(isoDate, 6, 2)), CLng(Right$(isoDate, 2)))
End Sub

Public Sub Harness_SetNumber(ByVal cellName As String, ByVal Value As String)
    If Len(Trim$(Value)) = 0 Then
        ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).ClearContents
    Else
        ThisWorkbook.Names(cellName).RefersToRange.Cells(1, 1).Value = CDbl(Value)
    End If
End Sub

Public Function Harness_TryWriteRequest(ByVal path As String) As String
    ' Build and write the request, returning "" on success or the error text on failure.
    ' Used for the Excel-side refusals, which must fail BEFORE Python is ever invoked.
    On Error Resume Next
    WriteRequestJson BuildRequest(), path
    If Err.Number <> 0 Then Harness_TryWriteRequest = Err.Description
    On Error GoTo 0
End Function

Public Function Harness_TypedRoundTrip(ByVal requestPath As String, _
                                       ByVal responsePath As String) As Long
    ' The generic path: cells + tables -> JSON -> command (waited on) -> response -> cells.
    WriteRequestJson BuildRequest(), requestPath
    Harness_TypedRoundTrip = RunPricingCommand(requestPath, responsePath)
    PopulateOutputs ReadResponseJson(responsePath)
End Function
