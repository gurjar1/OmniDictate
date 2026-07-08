; OmniDictate_Setup.iss
; Script for Inno Setup - v3.0.3

#ifndef AppVersion
#define AppVersion "3.0.3"
#endif
#ifndef SourceDir
#define SourceDir "dist\OmniDictate"
#endif
#ifndef InstallerOutputDir
#define InstallerOutputDir "InstallerOutput"
#endif
#ifndef CompressionMode
#define CompressionMode "lzma2/ultra64"
#endif
#ifndef SolidCompressionMode
#define SolidCompressionMode "yes"
#endif
#ifndef DiskSpanningMode
#define DiskSpanningMode "no"
#endif
#ifndef DiskSliceSizeMode
#define DiskSliceSizeMode "2100000000"
#endif
#ifndef SlicesPerDiskMode
#define SlicesPerDiskMode "1"
#endif
#ifndef DefaultDir
#define DefaultDir "{localappdata}\OmniDictate"
#endif
#ifndef PrivilegesRequiredMode
#define PrivilegesRequiredMode "lowest"
#endif
#ifndef ArchitecturesInstallMode
#define ArchitecturesInstallMode "x64compatible"
#endif

[Setup]
; --- Application Identification ---
AppId={{E71B4146-B5BC-4903-946E-ED954312E31A}} ; Unique GUID (KEEP THIS!)
AppName=OmniDictate
AppVersion={#AppVersion}
AppPublisher=KAPIL GURJAR
AppPublisherURL=https://github.com/gurjar1/OmniDictate
AppSupportURL=https://github.com/gurjar1/OmniDictate/issues
AppUpdatesURL=https://github.com/gurjar1/OmniDictate/releases

; --- Installation Directory ---
DefaultDirName={#DefaultDir}

; --- Installer Settings ---
; Release builds install per-user by default so dictation can be installed,
; launched, and removed without UAC. Admin/Program Files builds can override
; this with /DPrivilegesRequiredMode=admin and /DDefaultDir={autopf64}\OmniDictate.
PrivilegesRequired={#PrivilegesRequiredMode}
; Specify 64-bit install mode
ArchitecturesInstallIn64BitMode={#ArchitecturesInstallMode}
; Folder where the setup.exe will be created
OutputDir={#InstallerOutputDir}
; Name of the setup file
OutputBaseFilename=OmniDictate_Setup_v{#AppVersion}
; Icon for setup.exe (ensure icon.ico exists)
SetupIconFile=icon.ico
; Compression settings
Compression={#CompressionMode}
SolidCompression={#SolidCompressionMode}
DiskSpanning={#DiskSpanningMode}
DiskSliceSize={#DiskSliceSizeMode}
SlicesPerDisk={#SlicesPerDiskMode}
; Appearance
WizardStyle=modern
; Optional: Wizard images (ensure files exist)
WizardImageFile=wizard-image.bmp
WizardSmallImageFile=wizard-small-image.bmp
; Optional: Display LICENSE during setup (ensure LICENSE file exists)
LicenseFile=LICENSE
; Optional: Show info before install (ensure readme_before.txt exists)
InfoBeforeFile=readme_before.txt
; Optional: Show info after install (ensure readme_after.txt exists)
InfoAfterFile=readme_after.txt
; Ensure uninstall information is registered properly
Uninstallable=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Optional shortcut tasks
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy all contents of the PyInstaller output directory to the installation directory
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Ensure 'dist\OmniDictate' exists relative to this .iss file after running PyInstaller

[Icons]
; Start Menu shortcut (Primary)
Name: "{autoprograms}\OmniDictate"; Filename: "{app}\OmniDictate.exe"; IconFilename: "{app}\icon.ico"
; Desktop shortcut (Optional, based on Task)
Name: "{autodesktop}\OmniDictate"; Filename: "{app}\OmniDictate.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; Option to run the application after installation finishes
Filename: "{app}\OmniDictate.exe"; Description: "{cm:LaunchProgram,OmniDictate}"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
; Ensure the entire installation directory and its contents are removed on uninstall
Type: filesandordirs; Name: "{app}"
