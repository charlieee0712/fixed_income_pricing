Attribute VB_Name = "DemoActions"
' Demo-only buttons. These live in the demonstration workbook, NOT in the shipped bridge:
' RysePricingBridge.bas stays free of any knowledge of this sheet's layout.
'
' Each one calls the bridge's own public procedures, and adds the thing a live audience
' needs — the request and the answer visible ON THE SHEET, so nobody has to alt-tab into a
' temp folder to see what crossed the boundary.
Option Explicit

Private Const JSON_ROW As Long = 21          ' first row of the JSON panel
Private Const JSON_MAX As Long = 70          ' rows to clear / show at most


Public Sub Demo_Price()
    ' The button: price the bond AND show both JSON documents.
    Dim requestPath As String, responsePath As String, exitCode As Long

    On Error GoTo Failed
    requestPath = Environ$("TEMP") & "\ryse_demo_request.json"
    responsePath = Environ$("TEMP") & "\ryse_demo_response.json"

    Application.StatusBar = "Pricing..."
    WriteRequestJson BuildVanillaRequest(), requestPath
    exitCode = RunPricingCommand(requestPath, responsePath)

    If Len(Dir$(responsePath)) = 0 Then
        Application.StatusBar = False
        MsgBox "The pricing runner produced no answer (exit code " & exitCode & ")." & vbCrLf & _
               "Check the Runner command cell.", vbExclamation, "RYSE pricing demo"
        Exit Sub
    End If

    PopulateVanillaOutputs ReadResponseJson(responsePath)
    ShowJsonPanel requestPath, responsePath
    Application.StatusBar = False
    Exit Sub

Failed:
    Application.StatusBar = False
    MsgBox "Demo error " & Err.Number & ": " & Err.Description, vbExclamation, "RYSE pricing demo"
End Sub


Public Sub Demo_Clear()
    ' Empty the results and the JSON panel, so the next click is a clean reveal.
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(1)
    ws.Range("E5:E18").ClearContents
    ws.Range("A" & JSON_ROW & ":F" & (JSON_ROW + JSON_MAX)).ClearContents
    ws.Range("A1").Select
End Sub


Public Sub Demo_LoadSavedAnswer()
    ' The no-Python fallback: map the committed example response into the sheet. One click,
    ' no file browser — the path is derived from where this workbook sits in the repository.
    Dim path As String
    path = RepoRoot() & "\integrations\excel_vba\examples\vanilla_response_v1.json"

    If Len(Dir$(path)) = 0 Then
        MsgBox "Saved example not found at:" & vbCrLf & path & vbCrLf & vbCrLf & _
               "Keep the workbook inside the repository folder.", vbExclamation, _
               "RYSE pricing demo"
        Exit Sub
    End If

    PopulateVanillaOutputs ReadResponseJson(path)
    ShowJsonPanel vbNullString, path
End Sub


Private Sub ShowJsonPanel(ByVal requestPath As String, ByVal responsePath As String)
    ' Put the two documents side by side on the sheet: request in column A, answer in D.
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Worksheets(1)

    ws.Range("A" & JSON_ROW & ":F" & (JSON_ROW + JSON_MAX)).ClearContents
    ws.Range("A" & JSON_ROW).Value = "WHAT EXCEL SENT"
    ws.Range("D" & JSON_ROW).Value = "WHAT CAME BACK"
    ws.Range("A" & JSON_ROW & ",D" & JSON_ROW).Font.Bold = True
    ws.Range("A" & JSON_ROW & ",D" & JSON_ROW).Font.Color = RGB(18, 48, 92)

    If Len(requestPath) > 0 Then WriteLines ws, "A", requestPath
    WriteLines ws, "D", responsePath

    With ws.Range("A" & (JSON_ROW + 1) & ":F" & (JSON_ROW + JSON_MAX)).Font
        .Name = "Consolas"
        .Size = 8
    End With
End Sub


Private Sub WriteLines(ByVal ws As Worksheet, ByVal column As String, ByVal path As String)
    ' One file line per cell — a JSON document reads naturally down a column.
    Dim lines() As String, i As Long, n As Long
    lines = Split(Replace(ReadUtf8(path), vbCrLf, vbLf), vbLf)
    n = UBound(lines)
    If n > JSON_MAX - 2 Then n = JSON_MAX - 2
    For i = 0 To n
        ws.Range(column & (JSON_ROW + 1 + i)).Value = "'" & lines(i)
    Next i
End Sub


Private Function ReadUtf8(ByVal path As String) As String
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2
    stream.Charset = "utf-8"
    stream.Open
    stream.LoadFromFile path
    ReadUtf8 = stream.ReadText
    stream.Close
End Function


Private Function RepoRoot() As String
    ' ...\<repo>\integrations\excel_vba\demo  ->  ...\<repo>
    Dim fso As Object, folder As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set folder = fso.GetFolder(ThisWorkbook.path)
    RepoRoot = folder.ParentFolder.ParentFolder.ParentFolder.path
End Function
