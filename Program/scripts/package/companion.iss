; Per-user Windows installer for the self-contained bundle (scripts/package/build_bundle.py).
; Build: ISCC.exe /DAppVersion=<version> /DSourceDir=<unpacked ProsperoCompanion> /DOutputDir=<dir> companion.iss
; Installs into %LOCALAPPDATA%\Programs\Prospero Companion without administrator rights. The
; workspace in %LOCALAPPDATA%\ProsperoCompanion is never installed, replaced or removed here.

#ifndef AppVersion
  #error Pass /DAppVersion=<version>
#endif
#ifndef SourceDir
  #error Pass /DSourceDir=<unpacked bundle>
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
; Fixed for every Companion release, and unrelated to Prospero's Study.
AppId={{82941F85-FF26-49CE-80BA-9B592D72162F}
AppName=Prospero Companion
AppVersion={#AppVersion}
AppVerName=Prospero Companion {#AppVersion}
AppPublisher=Prospero Companion
AppPublisherURL=https://github.com/vantaloomin/prosperos-companion
DefaultDirName={autopf}\Prospero Companion
DisableDirPage=auto
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=ProsperoCompanion-{#AppVersion}-win-x64-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Prospero Companion
UninstallDisplayIcon={app}\runtime\python.exe
; A running Companion holds files in {app}; Restart Manager offers to close it first.
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[InstallDelete]
; An upgrade starts from clean program files, so modules removed in a release do not linger.
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\runtime"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Prospero Companion"; Filename: "{app}\runtime\python.exe"; Parameters: "-I -m companion.launch"; WorkingDir: "{app}"; Comment: "Start Prospero Companion"
Name: "{autodesktop}\Prospero Companion"; Filename: "{app}\runtime\python.exe"; Parameters: "-I -m companion.launch"; WorkingDir: "{app}"; Comment: "Start Prospero Companion"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\python.exe"; Parameters: "-I -m companion.launch"; WorkingDir: "{app}"; Description: "Start Prospero Companion"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Bytecode written at run time. The workspace and its backups stay where they are.
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\runtime"
