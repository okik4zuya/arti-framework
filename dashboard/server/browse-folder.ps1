<#
.SYNOPSIS
  Shows the modern Explorer-style folder picker (Vista+ IFileOpenDialog with
  FOS_PICKFOLDERS -- the same dialog OpenFileDialog uses, restricted to
  folders) and prints the chosen absolute path to stdout. Prints nothing if
  the user cancels. Invoked by server.py -- not meant to be run standalone.

  Windows PowerShell 5.1 targets .NET Framework, where
  System.Windows.Forms.FolderBrowserDialog still renders as the legacy
  Windows-95-era tree dialog (no address bar, no search, no typing a path).
  This COM-interop shim calls the real IFileDialog API directly instead.
#>
Add-Type -AssemblyName System.Windows.Forms

Add-Type -Language CSharp -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

namespace ArtiFolderPicker {
    [ComImport, Guid("42f85136-db7e-439c-85f1-e4075d135fc8"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IFileDialog {
        [PreserveSig] int Show(IntPtr parent);
        void SetFileTypes(uint cFileTypes, IntPtr rgFilterSpec);
        void SetFileTypeIndex(uint iFileType);
        void GetFileTypeIndex(out uint piFileType);
        void Advise(IntPtr pfde, out uint pdwCookie);
        void Unadvise(uint dwCookie);
        void SetOptions(uint fos);
        void GetOptions(out uint pfos);
        void SetDefaultFolder(IShellItem psi);
        void SetFolder(IShellItem psi);
        void GetFolder(out IShellItem ppsi);
        void GetCurrentSelection(out IShellItem ppsi);
        void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string pszName);
        void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string pszName);
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string pszTitle);
        void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string pszText);
        void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string pszLabel);
        void GetResult(out IShellItem ppsi);
        void AddPlace(IShellItem psi, uint fdap);
        void SetDefaultExtension([MarshalAs(UnmanagedType.LPWStr)] string pszDefaultExtension);
        void Close(int hr);
        void SetClientGuid(ref Guid guid);
        void ClearClientData();
        void SetFilter(IntPtr pFilter);
    }

    [ComImport, Guid("43826d1e-e718-42ee-bc55-a1e261c37bfe"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IShellItem {
        void BindToHandler(IntPtr pbc, ref Guid bhid, ref Guid riid, out IntPtr ppv);
        void GetParent(out IShellItem ppsi);
        void GetDisplayName(uint sigdnName, out IntPtr ppszName);
        void GetAttributes(uint sfgaoMask, out uint psfgaoAttribs);
        void Compare(IShellItem psi, uint hint, out int piOrder);
    }

    [ComImport, Guid("DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7")]
    public class FileOpenDialogRCW { }

    public static class FolderPicker {
        const uint FOS_PICKFOLDERS = 0x00000020;
        const uint FOS_FORCEFILESYSTEM = 0x00000040;
        const uint SIGDN_FILESYSPATH = 0x80058000;

        public static string Pick(IntPtr owner) {
            var dialog = (IFileDialog)new FileOpenDialogRCW();
            dialog.SetOptions(FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM);
            dialog.SetTitle("Select a project folder");
            int hr = dialog.Show(owner);
            if (hr != 0) return null; // user cancelled (HRESULT_FROM_WIN32(ERROR_CANCELLED) or similar)

            IShellItem result;
            dialog.GetResult(out result);
            IntPtr pszPath;
            result.GetDisplayName(SIGDN_FILESYSPATH, out pszPath);
            string path = Marshal.PtrToStringUni(pszPath);
            Marshal.FreeCoTaskMem(pszPath);
            return path;
        }
    }
}
"@

# server.py spawns this script from a background (often windowless) python process,
# which Windows denies foreground-activation rights -- without a TopMost owner window
# the dialog only flashes in the taskbar instead of popping to front.
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.StartPosition = "CenterScreen"
$owner.ShowInTaskbar = $false
$owner.Size = New-Object System.Drawing.Size(0, 0)
$owner.Show()
$owner.Activate()

try {
    $path = [ArtiFolderPicker.FolderPicker]::Pick($owner.Handle)
    if ($path) {
        Write-Output $path
    }
} finally {
    $owner.Close()
}
