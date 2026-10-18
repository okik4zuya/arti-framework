; arti-installer.nsi — NSIS installer for the ARTi framework (Windows)
; Build with: installer\build_installer.bat  (invokes makensis after staging payload\bin\)
;
; Scope: static payload only (tracked repo files + vendored poppler/tesseract/ripgrep), then delegates
; to install.ps1 for everything else (vendored Python, pip installs, skill junctions, desktop
; shortcut) - one source of truth for that part, unchanged by this installer. No Researcher
; Profile prompts, no per-project scaffolding - that stays the job of the ARTi-setup skill,
; run afterward inside Claude Code.
;
; Per-user, no-admin install (unlike artipdf's own installer.nsi, which this borrows structure
; from): default install dir is $PROFILE\.arti, RequestExecutionLevel is "user".

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"

!insertmacro GetParameters
!insertmacro GetOptions

; License key typed on the key page (or given as /KEY=... for silent installs); FreshInstall = 1 when
; no earlier ARTi install was found, so a failed activation can remove what this run just wrote.
Var LicenseKey
Var KeyInput
Var KeyStatus
Var FreshInstall
Var AsideFailed

; An update over an existing install first moves the tracked code folders out of the way (the installer only
; adds and overwrites, so a file the new version no longer ships would stay behind). Rename, not delete, so that a
; locked folder (ARTi or a Claude Code session still using it) is found before anything is lost: AsideFailed then
; holds its name and the caller puts back what was already moved. $INSTDIR\<N>.old-install is deleted after the copy.
!macro AsideItem N
    ${If} $AsideFailed == ""
    ${AndIf} ${FileExists} "$INSTDIR\${N}\*.*"
        ClearErrors
        Rename "$INSTDIR\${N}" "$INSTDIR\${N}.old-install"
        ${If} ${Errors}
            StrCpy $AsideFailed "${N}"
        ${EndIf}
    ${EndIf}
!macroend

!macro PutBackItem N
    ${If} ${FileExists} "$INSTDIR\${N}.old-install\*.*"
        Rename "$INSTDIR\${N}.old-install" "$INSTDIR\${N}"
    ${EndIf}
!macroend

; Removes the skill junctions, the install folder and the Desktop shortcut. Shared by the uninstaller
; and by the installer's "activation failed on a fresh install" path. P is a label prefix so the
; labels stay unique per expansion.
!macro RemoveArtiInstall P
    FindFirst $0 $1 "$PROFILE\.claude\skills\*.*"
    ${P}loop:
        StrCmp $1 "" ${P}done
        StrCmp $1 "." ${P}next
        StrCmp $1 ".." ${P}next
        IfFileExists "$PROFILE\.claude\skills\$1\*.*" 0 ${P}next
        RMDir "$PROFILE\.claude\skills\$1"
    ${P}next:
        FindNext $0 $1
        Goto ${P}loop
    ${P}done:
    FindClose $0
    ; $INSTDIR is this process's working directory (SetOutPath), and Windows will not delete a folder that is
    ; some process's current directory: the failed-activation cleanup left an empty .arti behind (Sandbox A1c, 2026-10-17).
    SetOutPath "$TEMP"
    RMDir /r "$INSTDIR"
    Delete "$DESKTOP\ARTi Framework.lnk"
!macroend

; ---------------------------------------------------------------------------
; Constants — APP_VERSION is passed in by build_installer.bat via /DAPP_VERSION=,
; read from ..\VERSION's FRAMEWORK_VERSION line, so this file never needs to be
; hand-edited to bump the version. Falls back to a placeholder if invoked directly
; with plain makensis (not the normal build path).
; ---------------------------------------------------------------------------
!ifndef APP_VERSION
  !define APP_VERSION "0.0.0-dev"
!endif
!define APP_NAME        "ARTi Framework"
!define APP_PUBLISHER    "okik4zuya"
!define UNINSTALL_KEY    "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; Licensing server for the pre-install key check, read from the same config.json the client uses, so the
; two can never disagree. Falls back to the production address if the file's layout ever changes.
!define API_BASE "https://lisensi.arti.ai.id/v1"
!searchparse /noerrors /file "..\tools\arti-license\config.json" `"api_base": "` API_BASE_FOUND `"`
!ifdef API_BASE_FOUND
  !undef API_BASE
  !define API_BASE "${API_BASE_FOUND}"
!endif

; The payload now holds a complete Python (about 600 MB unpacked), so compress it as one solid block.
SetCompressor /SOLID lzma
SetCompressorDictSize 64

Name "${APP_NAME}"
OutFile "dist\ArtiFrameworkSetup-${APP_VERSION}.exe"
InstallDir "$PROFILE\.arti"
InstallDirRegKey HKCU "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel user

!define MUI_ABORTWARNING
!define MUI_ICON "..\logo\export\icon\arti-launcher.ico"
!define MUI_UNICON "..\logo\export\icon\arti-launcher.ico"

!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchDashboard
!define MUI_FINISHPAGE_RUN_TEXT "Launch ARTi dashboard"
!define MUI_FINISHPAGE_TEXT_LARGE
!define MUI_FINISHPAGE_TEXT "Setup has finished installing ${APP_NAME}.$\r$\n$\r$\nNext, open Claude Code and say $\"set up ARTi$\" to create your Researcher Profile."

; ---------------------------------------------------------------------------
; Pages
; ---------------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
Page custom KeyPageShow KeyPageLeave
ShowInstDetails show
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; Sets $0 to 1 when the WebView2 Runtime binary exists (same registry-then-file test as dashboard\app.py), else 0.
; The registry alone is not enough: a machine can carry the registration without msedgewebview2.exe.
Function CheckWebView2
    StrCpy $0 0
    ${ForEach} $2 0 2 + 1
        ${If} $2 == 0
            SetRegView 32
            ReadRegStr $1 HKLM "SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
            StrCpy $3 "$PROGRAMFILES32"
        ${ElseIf} $2 == 1
            SetRegView 64
            ReadRegStr $1 HKLM "SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
            StrCpy $3 "$PROGRAMFILES32"
        ${Else}
            SetRegView 64
            ReadRegStr $1 HKCU "SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
            StrCpy $3 "$LOCALAPPDATA"
        ${EndIf}
        ${If} $1 != ""
            ; FileOpen, not ${FileExists}: the Windows Sandbox base image lists a msedgewebview2.exe that cannot be opened
            ; (dashboard\app.py's is_file() rejects it), and ${FileExists} accepted that phantom entry.
            ClearErrors
            FileOpen $4 "$3\Microsoft\EdgeWebView\Application\$1\msedgewebview2.exe" r
            ${IfNot} ${Errors}
                FileClose $4
                StrCpy $0 1
                ${ExitFor}
            ${EndIf}
        ${EndIf}
    ${Next}
    SetRegView 32
FunctionEnd


Function LaunchDashboard
    ; Without the WebView2 Runtime the dashboard would open as a browser tab, which looks like a failed install
    ; when the runtime is still downloading on a slow connection. Say so instead of opening a tab.
    Call CheckWebView2
    ${If} $0 == 0
        MessageBox MB_OK|MB_ICONINFORMATION "ARTi is installed, but its window needs the Microsoft WebView2 Runtime, which is not ready yet (it can still be downloading on a slow connection).$\r$\n$\r$\nWait a few minutes, then open ARTi Framework from the Desktop shortcut."
        Return
    ${EndIf}
    ; Launch via the vendored pythonw.exe (install.ps1 has just installed it), same target the
    ; Desktop shortcut points at - not a bare .py double-click, which would use whatever python
    ; the system has associated (if any) instead of the one this installer just set up.
    ExecShell "" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\dashboard\app.py"'
FunctionEnd

; Checks $LicenseKey (format, checksum, then a read-only look at the licensing server) BEFORE anything is
; written to disk. Leaves the exit code in $0 and a plain sentence in $2; $0 = 0 means go ahead. Needs no
; Python: it is a PowerShell script unpacked to the installer's temp folder. The key travels in an
; environment variable, so a quote typed into the key box cannot break the command line.
Function PrecheckKey
    InitPluginsDir
    File "/oname=$PLUGINSDIR\precheck.ps1" "precheck.ps1"
    System::Call 'Kernel32::SetEnvironmentVariable(t "ARTI_PRECHECK_KEY", t "$LicenseKey")'
    nsExec::ExecToStack 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\precheck.ps1" -Api "${API_BASE}"'
    Pop $0
    Pop $2
    System::Call 'Kernel32::SetEnvironmentVariable(t "ARTI_PRECHECK_KEY", t "")'
    ${If} $0 != 0
    ${AndIf} $2 == ""
        StrCpy $2 "The license key could not be checked."
    ${EndIf}
FunctionEnd

Function .onInit
    ; Silent installs pass the key on the command line: ArtiFrameworkSetup.exe /S /KEY=ARTI-XXXX-...
    ${GetParameters} $0
    ${GetOptions} $0 "/KEY=" $LicenseKey
    ; A key given on the command line is checked here, before the install starts. An update over an
    ; activated install has no key to check.
    ${If} $LicenseKey != ""
    ${AndIfNot} ${FileExists} "$INSTDIR\license.json"
        Call PrecheckKey
        ${If} $0 != 0
            ${IfNot} ${Silent}
                MessageBox MB_OK|MB_ICONSTOP "ARTi was not installed.$\r$\n$\r$\n$2"
            ${EndIf}
            SetErrorLevel 2
            Abort
        ${EndIf}
    ${EndIf}
FunctionEnd

Function KeyPageShow
    ; An update over an activated install, or a key given with /KEY=, needs no key page.
    IfFileExists "$INSTDIR\license.json" skip
    ${If} $LicenseKey != ""
        Abort
    ${EndIf}
    !insertmacro MUI_HEADER_TEXT "License key" "Enter the key you received after purchase."
    nsDialogs::Create 1018
    Pop $0
    ${NSD_CreateLabel} 0 0 100% 36u "Enter your license key (ARTI-XXXX-XXXX-XXXX-XXXX).$\r$\nThis computer needs an internet connection once, to activate. The key is checked before anything is installed."
    Pop $0
    ${NSD_CreateText} 0 44u 100% 12u ""
    Pop $KeyInput
    ${NSD_CreateLabel} 0 62u 100% 12u ""
    Pop $KeyStatus
    nsDialogs::Show
    Return
    skip:
    Abort
FunctionEnd

Function KeyPageLeave
    ${NSD_GetText} $KeyInput $LicenseKey
    StrLen $0 $LicenseKey
    ${If} $0 < 19
        MessageBox MB_OK|MB_ICONEXCLAMATION "Enter your license key (ARTI-XXXX-XXXX-XXXX-XXXX)."
        Abort
    ${EndIf}
    ; Check it now, while nothing has been written: a wrong key keeps the user on this page.
    ; The check takes a few seconds and the window does not repaint meanwhile, so show a status line first
    ; and lock the buttons so it cannot be clicked twice.
    ${NSD_SetText} $KeyStatus "Checking your license key, please wait..."
    System::Call 'user32::UpdateWindow(p $KeyStatus)'
    GetDlgItem $3 $HWNDPARENT 1
    EnableWindow $3 0
    GetDlgItem $4 $HWNDPARENT 3
    EnableWindow $4 0
    Call PrecheckKey
    EnableWindow $3 1
    EnableWindow $4 1
    ${If} $0 != 0
        ${NSD_SetText} $KeyStatus ""
        MessageBox MB_OK|MB_ICONEXCLAMATION "$2"
        Abort
    ${EndIf}
    ${NSD_SetText} $KeyStatus "Key accepted. Installing..."
FunctionEnd

; ---------------------------------------------------------------------------
; Install
; ---------------------------------------------------------------------------
Section "Install" SEC01
    ${If} ${FileExists} "$INSTDIR\VERSION"
        StrCpy $FreshInstall 0
    ${Else}
        StrCpy $FreshInstall 1
    ${EndIf}

    ; Update over an existing install: tools, skills, dashboard and logo are code only (the researcher's data is in
    ; memory, voice-profiles, license.json, mcp-keys.json ...; the audit is in memory/memories/installer-update-safety-plan.md),
    ; so they are replaced as a whole, the same as "Update now" does. Done before anything is written: if one of the
    ; folders is in use, put back what was moved and stop without changing the install.
    ${If} $FreshInstall == 0
        ; $INSTDIR may be this process's working directory, which Windows will not move or delete (see RemoveArtiInstall).
        SetOutPath "$TEMP"
        StrCpy $AsideFailed ""
        ; leftovers of an earlier run that was interrupted after the move
        RMDir /r "$INSTDIR\tools.old-install"
        RMDir /r "$INSTDIR\skills.old-install"
        RMDir /r "$INSTDIR\dashboard.old-install"
        RMDir /r "$INSTDIR\logo.old-install"
        !insertmacro AsideItem "tools"
        !insertmacro AsideItem "skills"
        !insertmacro AsideItem "dashboard"
        !insertmacro AsideItem "logo"
        ${If} $AsideFailed != ""
            !insertmacro PutBackItem "tools"
            !insertmacro PutBackItem "skills"
            !insertmacro PutBackItem "dashboard"
            !insertmacro PutBackItem "logo"
            MessageBox MB_OK|MB_ICONSTOP "ARTi could not be updated, because the folder $INSTDIR\$AsideFailed is in use. Nothing was changed.$\r$\n$\r$\nClose ARTi (the dashboard window), every Claude Code session and any terminal or File Explorer window that is open inside the ARTi folder, then run this installer again." /SD IDOK
            SetErrorLevel 3
            Quit
        ${EndIf}
    ${EndIf}

    SetOutPath "$INSTDIR"

    ; The WebView2 Runtime (needed for the dashboard window) is the slowest download on a clean Windows 10.
    ; Start it in the background now, before the big file copy, so both happen at the same time; install.ps1
    ; later waits for it (lock file) instead of installing it a second time.
    File "..\install.ps1"
    ; Plain Exec (and powershell's own -WindowStyle Hidden) still flash a console, because the console is created
    ; before powershell can hide it. ExecShell with SW_HIDE passes the hidden state in at process creation.
    ExecShell "open" "powershell.exe" '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$INSTDIR\install.ps1" -OnlyWebView2' SW_HIDE

    DetailPrint "Copying ARTi files and Python (about 600 MB unpacked, this takes a minute)..."

    ; Tracked repo content (mirrors $TrackedItems / TRACKED_ITEMS in install.ps1 / install.sh; neither ships
    ; installer/ itself, clients never build the installer, and mcp-keys.json is never shipped)
    ; tools\arti-compose\examples\out and \panels are git-ignored render output (about 4 MB), never part of a release;
    ; no other folder under tools, skills, dashboard or logo is named out or panels.
    ; Always `File /r "..\<dir>\*.*"` with SetOutPath, never `File /r "..\<dir>"`: with a bare directory name
    ; makensis searches the whole parent tree for anything with that name, so on the maintainer's machine it also
    ; packed every folder called tools or skills from the vendored dev Python (fastmcp, mcp, pywin32, typer) and from
    ; installer\payload. Found 2026-10-17 when verify_payload.py's mcp check failed; verify_payload.py now rejects
    ; any file that is neither tracked nor part of the staged payload.
    SetOutPath "$INSTDIR\tools"
    File /r /x "__pycache__" /x "*.pyc" /x "out" /x "panels" "..\tools\*.*"
    SetOutPath "$INSTDIR\skills"
    File /r /x "__pycache__" /x "*.pyc" "..\skills\*.*"
    ; server.log is runtime state (app.py truncates/recreates it on each fresh spawn, gitignored) --
    ; never something to ship. Without this exclude, whatever happens to be on the maintainer's own
    ; machine at build time gets baked into every install.
    SetOutPath "$INSTDIR\dashboard"
    File /r /x "server.log" /x "__pycache__" /x "*.pyc" "..\dashboard\*.*"
    SetOutPath "$INSTDIR\logo"
    File /r "..\logo\*.*"
    SetOutPath "$INSTDIR"
    File "..\CLAUDE.md"
    File "..\CAPABILITIES.md"
    File "..\LICENSE.txt"
    File "..\.mcp.json"
    File "..\README.md"
    File "..\UPDATING.md"
    File "..\prompt-templates.md"
    File "..\install.sh"
    ; (install.ps1 was already written above, before the background WebView2 step started)
    File "..\install.bat"
    File "..\VERSION"
    File "..\.gitignore"

    ; Vendored poppler/tesseract/ripgrep, pre-staged by build_installer.bat into payload\bin
    ; (ripgrep staging is optional -- a missing RIPGREP_DIR just means this recurses over
    ; whatever payload\bin subfolders exist, and the app falls back to its pure-Python
    ; search path when rg.exe isn't present)
    SetOutPath "$INSTDIR\bin"
    File /r "payload\bin\*.*"

    ; Ready-made Python with every package installed (built by stage_python.py). install.ps1 sees its stamps
    ; (INSTALLED_VERSION, REQUIREMENTS_SHA256) and skips the download and pip. ifnewer: an update over an
    ; existing install leaves unchanged files alone, so a running python.exe is never overwritten needlessly.
    SetOutPath "$INSTDIR\python"
    SetOverwrite ifnewer
    File /r "payload\python\*.*"
    SetOverwrite on
    SetOutPath "$INSTDIR"

    ; The old code folders moved aside at the start of an update are no longer needed.
    RMDir /r "$INSTDIR\tools.old-install"
    RMDir /r "$INSTDIR\skills.old-install"
    RMDir /r "$INSTDIR\dashboard.old-install"
    RMDir /r "$INSTDIR\logo.old-install"

    ; Everything else (vendored Python, pip installs, skill junctions, desktop shortcut) is
    ; install.ps1's job - one source of truth, unchanged by this installer.
    DetailPrint "Running install.ps1 (vendored Python, skills, shortcut; may wait for the WebView2 Runtime on a slow connection)..."
    ; This installer activates the license itself (below), so install.ps1 must not prompt for a key.
    System::Call 'Kernel32::SetEnvironmentVariable(t "ARTI_LICENSE_HANDLED", t "1")'
    nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install.ps1"'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_OK|MB_ICONEXCLAMATION "install.ps1 exited with code $0 - some setup steps (Python, skill links, shortcut) may be incomplete. You can re-run $INSTDIR\install.ps1 later to retry."
    ${EndIf}

    ; ---- License activation (mandatory, needs internet) ----
    ; Skipped on an update over an already-activated install. On a fresh install a failure removes
    ; everything this run wrote; on an old install without a license the files stay and the dashboard
    ; stays locked until Settings > License is filled in.
    ${IfNot} ${FileExists} "$INSTDIR\license.json"
        DetailPrint "Activating license..."
        nsExec::ExecToStack '"$INSTDIR\python\python.exe" "$INSTDIR\tools\arti-license\cli.py" activate "$LicenseKey"'
        Pop $0
        Pop $2
        ${If} $0 != 0
            ${If} $LicenseKey == ""
                StrCpy $2 "No license key was given (silent installs need /KEY=ARTI-XXXX-XXXX-XXXX-XXXX)."
            ${EndIf}
            ${If} $FreshInstall == 1
                MessageBox MB_OK|MB_ICONSTOP "Activation failed, so ARTi was not installed.$\r$\n$\r$\n$2$\r$\nCheck the key and your internet connection, then run the installer again."
                ; Only wipe a folder named .arti (the default); a folder the user picked may hold other files.
                StrCpy $3 $INSTDIR 5 -5
                ${If} $3 == ".arti"
                    !insertmacro RemoveArtiInstall "fail"
                ${Else}
                    MessageBox MB_OK|MB_ICONINFORMATION "Files were copied to $INSTDIR. Delete that folder by hand if you do not want to keep them."
                ${EndIf}
                ; Abort here would leave the progress page open with a lone "Cancel" button (.onInstFailed did not
                ; run after Abort in a section, Sandbox A1c 2026-10-17); nothing is left to show, so exit with code 2.
                SetErrorLevel 2
                Quit
            ${Else}
                MessageBox MB_OK|MB_ICONEXCLAMATION "Activation failed:$\r$\n$\r$\n$2$\r$\nARTi was updated, but the dashboard stays locked until you activate in Settings > License."
            ${EndIf}
        ${EndIf}
    ${EndIf}

    WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"

    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\logo\export\icon\arti-launcher.ico"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1

    ; EstimatedSize wants KB
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "EstimatedSize" "$0"

    ; Explorer folder context menu: "Register as ARTi Project" -- both when
    ; right-clicking a folder itself and when right-clicking inside one (its
    ; background). Per-user install (no admin), so these go under
    ; HKCU\Software\Classes rather than HKCR (writing HKCR directly is
    ; unreliable without admin rights).
    WriteRegStr HKCU "Software\Classes\Directory\shell\RegisterArtiProject" "" "Register as ARTi Project"
    WriteRegStr HKCU "Software\Classes\Directory\shell\RegisterArtiProject" "Icon" "$INSTDIR\logo\export\icon\arti-launcher.ico"
    WriteRegStr HKCU "Software\Classes\Directory\shell\RegisterArtiProject\command" "" '"$INSTDIR\python\pythonw.exe" "$INSTDIR\dashboard\server\register_project_cli.py" "%1"'

    WriteRegStr HKCU "Software\Classes\Directory\Background\shell\RegisterArtiProject" "" "Register as ARTi Project"
    WriteRegStr HKCU "Software\Classes\Directory\Background\shell\RegisterArtiProject" "Icon" "$INSTDIR\logo\export\icon\arti-launcher.ico"
    WriteRegStr HKCU "Software\Classes\Directory\Background\shell\RegisterArtiProject\command" "" '"$INSTDIR\python\pythonw.exe" "$INSTDIR\dashboard\server\register_project_cli.py" "%V"'

    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; ---------------------------------------------------------------------------
; Uninstall
; ---------------------------------------------------------------------------
Section "Uninstall"
    ; Unlink skill junctions, then delete the install folder and the Desktop shortcut.
    !insertmacro RemoveArtiInstall "un"

    DeleteRegKey HKCU "${UNINSTALL_KEY}"
    DeleteRegKey HKCU "Software\${APP_NAME}"
    DeleteRegKey HKCU "Software\Classes\Directory\shell\RegisterArtiProject"
    DeleteRegKey HKCU "Software\Classes\Directory\Background\shell\RegisterArtiProject"
SectionEnd
