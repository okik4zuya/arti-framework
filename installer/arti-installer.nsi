; arti-installer.nsi — NSIS installer for the ARTi framework (Windows)
; Build with: installer\build_installer.bat  (invokes makensis after staging payload\bin\)
;
; Scope: static payload only (tracked repo files + vendored poppler/tesseract), then delegates
; to install.ps1 for everything else (vendored Python, pip installs, skill junctions, desktop
; shortcut) - one source of truth for that part, unchanged by this installer. No Researcher
; Profile prompts, no per-project scaffolding - that stays the job of the ARTi-setup skill,
; run afterward inside Claude Code.
;
; Per-user, no-admin install (unlike artipdf's own installer.nsi, which this borrows structure
; from): default install dir is $PROFILE\.arti, RequestExecutionLevel is "user".

!include "MUI2.nsh"
!include "FileFunc.nsh"

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
!insertmacro MUI_PAGE_DIRECTORY
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

; ---------------------------------------------------------------------------
; Install
; ---------------------------------------------------------------------------
Section "Install" SEC01
    SetOutPath "$INSTDIR"

    ; Tracked repo content (mirrors $TrackedItems / TRACKED_ITEMS in install.ps1 / install.sh)
    File /r "..\tools"
    File /r "..\skills"
    File /r "..\dashboard"
    File /r "..\logo"
    File "..\CLAUDE.md"
    File "..\README.md"
    File "..\UPDATING.md"
    File "..\prompt-templates.md"
    File "..\install.ps1"
    File "..\install.sh"
    File "..\install.bat"
    File "..\VERSION"
    File "..\.gitignore"

    ; Vendored poppler/tesseract, pre-staged by build_installer.bat into payload\bin
    SetOutPath "$INSTDIR\bin"
    File /r "payload\bin\*.*"
    SetOutPath "$INSTDIR"

    ; Everything else (vendored Python, pip installs, skill junctions, desktop shortcut) is
    ; install.ps1's job - one source of truth, unchanged by this installer.
    DetailPrint "Running install.ps1 (vendored Python, skills, shortcut)..."
    nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install.ps1"'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_OK|MB_ICONEXCLAMATION "install.ps1 exited with code $0 - some setup steps (Python, skill links, shortcut) may be incomplete. You can re-run $INSTDIR\install.ps1 later to retry."
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

    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; ---------------------------------------------------------------------------
; Uninstall
; ---------------------------------------------------------------------------
Section "Uninstall"
    ; Unlink skill junctions this installer's install.ps1 run created, before the
    ; target directories themselves disappear along with $INSTDIR below.
    FindFirst $0 $1 "$PROFILE\.claude\skills\*.*"
    loop:
        StrCmp $1 "" done
        StrCmp $1 "." next
        StrCmp $1 ".." next
        IfFileExists "$PROFILE\.claude\skills\$1\*.*" 0 next
        RMDir "$PROFILE\.claude\skills\$1"
    next:
        FindNext $0 $1
        Goto loop
    done:
    FindClose $0

    RMDir /r "$INSTDIR"

    Delete "$DESKTOP\ARTi Framework.lnk"

    DeleteRegKey HKCU "${UNINSTALL_KEY}"
    DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd
