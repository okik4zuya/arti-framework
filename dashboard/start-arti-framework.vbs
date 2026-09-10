' SUPERSEDED: the "ARTi Framework" Desktop icon now launches app.py directly
' (pythonw.exe app.py) via a native pywebview window instead of a browser tab
' -- see dashboard/app.py and install.ps1's shortcut-generation step. Kept in
' the repo for reference only; no longer wired to any shortcut.
'
' --- original hidden-launcher behavior below, unchanged ---
'
' Liveness check first: if the dashboard server is already answering on
' 127.0.0.1:4174 (e.g. the researcher closed the browser tab earlier but never
' quit the server), skip spawning anything and just open a tab against it.
' Otherwise spawn pythonw.exe (the windowless twin of python.exe, vendored
' alongside it) hidden, wait briefly for it to come up, then open the tab.

Dim fso, shell, artiHome, dashboardDir, serverDir, pythonwExe, logPath
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

artiHome = shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.arti"
dashboardDir = artiHome & "\dashboard"
serverDir = dashboardDir & "\server"
pythonwExe = artiHome & "\python\pythonw.exe"
logPath = dashboardDir & "\server.log"

Function IsAlive()
    On Error Resume Next
    Dim http
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    http.SetTimeouts 400, 400, 400, 400
    http.Open "GET", "http://127.0.0.1:4174/api/ping", False
    http.Send
    IsAlive = (Err.Number = 0) And (http.Status = 200)
    On Error Goto 0
End Function

If Not IsAlive() Then
    ' Fresh spawn: truncate the log so a traceback is inspectable without a
    ' console window. A reused-server relaunch never touches it.
    If fso.FileExists(logPath) Then fso.DeleteFile logPath, True

    Dim cmd
    cmd = "cmd /c """"" & pythonwExe & """ """ & serverDir & "\server.py"" > """ & logPath & """ 2>&1"""
    shell.CurrentDirectory = serverDir
    shell.Run cmd, 0, False

    ' Wait briefly for /api/ping to respond before opening the tab.
    Dim tries
    tries = 0
    Do While (Not IsAlive()) And tries < 40
        WScript.Sleep 250
        tries = tries + 1
    Loop
End If

shell.Run "http://127.0.0.1:4174/", 1, False
