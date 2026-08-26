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
