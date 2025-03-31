; OmniDictate_Setup.iss
; Script for Inno Setup - v1.3 (Corrected Comments)

[Setup]
; --- Application Identification ---
AppId={{E71B4146-B5BC-4903-946E-ED954312E31A}} ; Unique GUID (KEEP THIS!)
AppName=OmniDictate
AppVersion=1.0.0
AppPublisher=KAPIL GURJAR
AppPublisherURL=https://github.com/gurjar1/OmniDictate
AppSupportURL=https://github.com/gurjar1/OmniDictate/issues
AppUpdatesURL=https://github.com/gurjar1/OmniDictate/releases

; --- Installation Directory ---
DefaultDirName={autopf64}\OmniDictate
; Install to 64-bit Program Files

; --- Installer Settings ---
; Requires admin privileges to install to Program Files
PrivilegesRequired=admin
; Specify 64-bit install mode
ArchitecturesInstallIn64BitMode=x64
; Folder where the setup.exe will be created
OutputDir=InstallerOutput
; Name of the setup file
OutputBaseFilename=OmniDictate_Setup_v1.0.0
; Icon for setup.exe (ensure icon.ico exists)
SetupIconFile=icon.ico
; Compression settings
Compression=lzma
SolidCompression=yes
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
Source: "dist\OmniDictate\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
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