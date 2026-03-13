; ============================================================
;  pyProspector — Inno Setup 6 installer script
;  Compile with:
;    "C:\Users\madson.unias\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
; ============================================================

#define MyAppName      "pyProspector"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Madson Germano"
#define MyAppExe       "pyProspector.exe"
#define MyAppURL       "https://github.com/zandargo/pyProspector"
#define MyAppIcon      "assets\icon\pyProspector01.ico"

[Setup]
; Unique application identifier — change this GUID if you fork the app
AppId={{5CF8A3D1-2B9E-4F07-8C1A-3D9E6F2A1B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Install per-user — no admin rights needed
PrivilegesRequired=lowest
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; Output
OutputDir=Output
OutputBaseFilename=pyProspector_Setup
SetupIconFile={#MyAppIcon}

; Compression
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Target 64-bit Windows
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy the full PyInstaller one-dir bundle (exe + _internal + playwright-browsers)
Source: "dist\pyProspector\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu entry — icon is embedded in the exe by PyInstaller
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
; Desktop shortcut (optional, selected by user during setup)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Offer to launch the app right after installation finishes
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove everything (including Playwright browser cache) on uninstall
Type: filesandordirs; Name: "{app}"
