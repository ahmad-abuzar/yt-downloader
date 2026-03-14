[Setup]
AppName=Universal Video Downloader
AppVersion=1.0
DefaultDirName={autopf}\Universal Video Downloader
DefaultGroupName=Universal Video Downloader
OutputDir=Output
OutputBaseFilename=VideoDownloader_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Files]
Source: "dist\VideoDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Universal Video Downloader"; Filename: "{app}\VideoDownloader.exe"
Name: "{autodesktop}\Universal Video Downloader"; Filename: "{app}\VideoDownloader.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
