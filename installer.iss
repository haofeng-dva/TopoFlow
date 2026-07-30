#define MyAppName "TopoFlow"
#define MyAppVersion "0.9.0-alpha"
#define MyAppExeName "TopoFlow.exe"
[Setup]
AppId={{64B4E9BC-3398-43D7-B792-E0AD9F2704BE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName=D:\TopoFlowApp
DefaultGroupName=TopoFlow
OutputDir=dist
OutputBaseFilename=TopoFlow-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
[Files]
Source: "dist\TopoFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"
[Icons]
Name: "{autoprograms}\TopoFlow"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TopoFlow"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 TopoFlow"; Flags: nowait postinstall skipifsilent

