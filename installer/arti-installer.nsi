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
Var FreshInstall

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
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Function LaunchDashboard
    ; Launch via the vendored pythonw.exe (install.ps1 has just installed it), same target the
    ; Desktop shortcut points at - not a bare .py double-click, which would use whatever python
    ; the system has associated (if any) instead of the one this installer just set up.
    ExecShell "" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\dashboard\app.py"'
FunctionEnd

Function .onInit
    ; Silent installs pass the key on the command line: ArtiFrameworkSetup.exe /S /KEY=ARTI-XXXX-...
    ${GetParameters} $0
    ${GetOptions} $0 "/KEY=" $LicenseKey
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
    ${NSD_CreateLabel} 0 0 100% 36u "Enter your license key (ARTI-XXXX-XXXX-XXXX-XXXX).$\r$\nThis computer needs an internet connection once, to activate. If activation fails, nothing is installed."
    Pop $0
    ${NSD_CreateText} 0 44u 100% 12u ""
    Pop $KeyInput
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
    SetOutPath "$INSTDIR"

    ; Tracked repo content (mirrors $TrackedItems / TRACKED_ITEMS in install.ps1 / install.sh; neither ships
    ; installer/ itself, clients never build the installer, and mcp-keys.json is never shipped)
    File /r /x "__pycache__" /x "*.pyc" "..\tools"
    File /r /x "__pycache__" /x "*.pyc" "..\skills"
    ; server.log is runtime state (app.py truncates/recreates it on each fresh spawn, gitignored) --
    ; never something to ship. Without this exclude, whatever happens to be on the maintainer's own
    ; machine at build time gets baked into every install.
    File /r /x "server.log" /x "__pycache__" /x "*.pyc" "..\dashboard"
    File /r "..\logo"
    File "..\CLAUDE.md"
    File "..\CAPABILITIES.md"
    File "..\LICENSE.txt"
    File "..\.mcp.json"
    File "..\README.md"
    File "..\UPDATING.md"
    File "..\prompt-templates.md"
    File "..\install.ps1"
    File "..\install.sh"
    File "..\install.bat"
    File "..\VERSION"
    File "..\.gitignore"

    ; Vendored poppler/tesseract/ripgrep, pre-staged by build_installer.bat into payload\bin
    ; (ripgrep staging is optional -- a missing RIPGREP_DIR just means this recurses over
    ; whatever payload\bin subfolders exist, and the app falls back to its pure-Python
    ; search path when rg.exe isn't present)
    SetOutPath "$INSTDIR\bin"
    File /r "payload\bin\*.*"
    SetOutPath "$INSTDIR"

    ; Everything else (vendored Python, pip installs, skill junctions, desktop shortcut) is
    ; install.ps1's job - one source of truth, unchanged by this installer.
    DetailPrint "Running install.ps1 (vendored Python, skills, shortcut)..."
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
                Abort
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
