Attribute VB_Name = "DemoBuilder"
' Builds the demonstration sheet: labels, input cells, result cells, named ranges and
' buttons. Run once by Build-DemoWorkbook.ps1, which then removes this module — the
' delivered workbook contains only the bridge and the JSON parser.
'
' The layout is done here, in VBA, rather than from PowerShell because the PowerShell COM
' binder types a property from its first use per call site: writing a label and then a
' number through the same call site throws.
Option Explicit

Public Sub Build_DemoSheet(ByVal runnerPath As String)
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(1)
    ws.Name = "Pricer"
    ws.Cells.Font.Name = "Segoe UI"
    ws.Cells.Font.Size = 10

    ' ---- title -------------------------------------------------------------------
    ws.Range("A1").Value = "RYSE fixed-income pricing — live demonstration"
    ws.Range("A1").Font.Size = 14
    ws.Range("A1").Font.Bold = True
    ws.Range("A2").Value = "Excel writes one JSON request, Python prices the bond, one JSON answer comes back."
    ws.Range("A2").Font.Italic = True

    ' ---- inputs ------------------------------------------------------------------
    Header ws.Range("A4"), "INPUTS  (edit these)"
    Label ws.Range("A5"), "Instrument"
    Label ws.Range("A6"), "Currency"
    Label ws.Range("A7"), "Coupon (% per year)"
    Label ws.Range("A8"), "Payments per year"
    Label ws.Range("A9"), "Maturity"
    Label ws.Range("A10"), "Valuation date"
    Label ws.Range("A11"), "Clean market price"
    Label ws.Range("A12"), "Spread shift (bp)"
    Label ws.Range("A13"), "Yield volatility"

    ws.Range("B5").Value = "DEMO-BOND-001"
    ws.Range("B6").Value = "USD"
    ws.Range("B7").Value = 6.5
    ws.Range("B8").Value = 2
    ws.Range("B9").Value = DateSerial(2017, 1, 15)
    ws.Range("B10").Value = DateSerial(2009, 3, 31)
    ws.Range("B11").Value = 94.25
    ws.Range("B12").Value = 10
    ws.Range("B13").Value = 0.15
    ws.Range("B9:B10").NumberFormat = "yyyy-mm-dd"
    ws.Range("B7").NumberFormat = "0.000"
    ws.Range("B11").NumberFormat = "0.0000"
    ws.Range("B13").NumberFormat = "0.00"
    InputBox_ ws.Range("B5:B13")

    Header ws.Range("A15"), "ENGINE"
    Label ws.Range("A16"), "Runner command"
    ws.Range("B16").Value = runnerPath
    InputBox_ ws.Range("B16")
    ws.Range("A17").Value = "The sheet knows only this one command. Point it at a packaged program " & _
                            "or a web service and nothing else changes."
    ws.Range("A17").Font.Italic = True
    ws.Range("A17").Font.Size = 9

    ' ---- results -----------------------------------------------------------------
    Header ws.Range("D4"), "RESULTS  (written by the engine)"
    Label ws.Range("D5"), "Status"
    Label ws.Range("D6"), "Model clean price"
    Label ws.Range("D7"), "Model dirty price"
    Label ws.Range("D8"), "Accrued interest"
    Label ws.Range("D9"), "Implied OAS (bp)"
    Label ws.Range("D10"), "Effective duration (years)"
    Label ws.Range("D11"), "DV01 (per 100 face)"
    Label ws.Range("D12"), "Convexity"
    Label ws.Range("D13"), "Price if spread tightens"
    Label ws.Range("D14"), "Price if spread widens"
    Label ws.Range("D15"), "Curve used"
    Label ws.Range("D16"), "Volatility"
    Label ws.Range("D17"), "Warnings"
    Label ws.Range("D18"), "Errors"

    ws.Range("E6:E8").NumberFormat = "0.0000"
    ws.Range("E9").NumberFormat = "0.00"
    ws.Range("E10").NumberFormat = "0.0000"
    ws.Range("E11").NumberFormat = "0.000000"
    ws.Range("E12").NumberFormat = "0.00"
    ws.Range("E13:E14").NumberFormat = "0.0000"
    OutputBox_ ws.Range("E5:E18")

    ' ---- names -------------------------------------------------------------------
    AddName "FIP_InstrumentId", ws.Range("B5")
    AddName "FIP_Currency", ws.Range("B6")
    AddName "FIP_CouponPct", ws.Range("B7")
    AddName "FIP_CouponFrequency", ws.Range("B8")
    AddName "FIP_MaturityDate", ws.Range("B9")
    AddName "FIP_ValuationDate", ws.Range("B10")
    AddName "FIP_CleanMarketPrice", ws.Range("B11")
    AddName "FIP_SpreadShiftBp", ws.Range("B12")
    AddName "FIP_YieldVolatility", ws.Range("B13")
    AddName "FIP_RunnerCommand", ws.Range("B16")

    AddName "FIP_Status", ws.Range("E5")
    AddName "FIP_ModelCleanPrice", ws.Range("E6")
    AddName "FIP_ModelDirtyPrice", ws.Range("E7")
    AddName "FIP_AccruedInterest", ws.Range("E8")
    AddName "FIP_ImpliedOASBp", ws.Range("E9")
    AddName "FIP_EffectiveDuration", ws.Range("E10")
    AddName "FIP_DV01", ws.Range("E11")
    AddName "FIP_Convexity", ws.Range("E12")
    AddName "FIP_TighterPrice", ws.Range("E13")
    AddName "FIP_WiderPrice", ws.Range("E14")
    AddName "FIP_CurveId", ws.Range("E15")
    AddName "FIP_VolatilityApplicability", ws.Range("E16")
    AddName "FIP_Warnings", ws.Range("E17")
    AddName "FIP_Errors", ws.Range("E18")

    ' ---- buttons -----------------------------------------------------------------
    AddButton ws, 20, 300, 150, 30, "Price this bond", "PriceVanillaBond"
    AddButton ws, 180, 300, 150, 30, "Show the request JSON", "WriteRequestToFile"
    AddButton ws, 340, 300, 170, 30, "Load a saved answer", "PopulateFromResponseFile"

    ws.Columns("A").ColumnWidth = 26
    ws.Columns("B").ColumnWidth = 34
    ws.Columns("C").ColumnWidth = 3
    ws.Columns("D").ColumnWidth = 26
    ws.Columns("E").ColumnWidth = 46
    ws.Range("E16:E18").WrapText = True
    ws.Rows("16:18").RowHeight = 15
    ws.Range("A1").Select
End Sub

Private Sub Header(ByVal cell As Range, ByVal text As String)
    cell.Value = text
    cell.Font.Bold = True
    cell.Font.Color = RGB(18, 48, 92)
End Sub

Private Sub Label(ByVal cell As Range, ByVal text As String)
    cell.Value = text
    cell.HorizontalAlignment = xlRight
End Sub

Private Sub InputBox_(ByVal target As Range)
    target.Interior.Color = RGB(255, 251, 230)
    target.Borders.LineStyle = xlContinuous
    target.Borders.Color = RGB(200, 190, 150)
End Sub

Private Sub OutputBox_(ByVal target As Range)
    target.Interior.Color = RGB(240, 244, 249)
    target.Borders.LineStyle = xlContinuous
    target.Borders.Color = RGB(190, 200, 215)
End Sub

Private Sub AddName(ByVal cellName As String, ByVal target As Range)
    ThisWorkbook.Names.Add Name:=cellName, RefersTo:=target
End Sub

Private Sub AddButton(ByVal ws As Worksheet, ByVal x As Double, ByVal y As Double, _
                      ByVal w As Double, ByVal h As Double, ByVal caption As String, _
                      ByVal macro As String)
    Dim b As Object
    Set b = ws.Buttons.Add(x, y, w, h)
    b.caption = caption
    b.OnAction = macro
End Sub
