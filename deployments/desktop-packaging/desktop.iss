#if DecodeVer(Ver, 3) != "7.1.1"
#error Use Inno Setup 7.1.1 to compile this edition
#endif

[Setup]
AppId=org.lychd.desktop.{#Edition}
AppName=LychD Personal Desktop
AppVersion={#Edition}
AppVerName=LychD Personal Desktop {#Edition}
DefaultDirName={localappdata}\Programs\LychD Editions\{#Edition}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
DisableDirPage=yes
DisableProgramGroupPage=yes
UsePreviousAppDir=no
CloseApplications=no
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=LychD Personal Desktop {#Edition}

[Files]
Source: "{#Payload}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
