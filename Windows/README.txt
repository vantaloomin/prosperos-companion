Prospero Companion on Windows - start here

1. Double-click install.bat once. It finds or installs Python and Node.js, then sets everything up.
2. Double-click launch.bat to start the Companion. It opens in your browser at http://127.0.0.1:8775.
   Keep its window open while you use it; close the window to stop.

Other scripts in this folder:
  update.bat           Gets the latest version and reinstalls. Close the Companion first.
  status.bat           Says whether the Companion is running.
  stop.bat             Stops the Companion if you lost its window.
  create-shortcut.bat  Puts a Prospero Companion shortcut on your desktop.
  dev.bat              Development mode, for working on the code.

Your companion's data is normally not in this folder. It lives in %LOCALAPPDATA%\ProsperoCompanion,
so updating or re-downloading the program keeps it. To keep it with the app instead (for example
on an external drive), use Settings > Data > "Move into the app folder": it then lives in a Data
folder here, which updates leave alone. The app itself is in the Program folder, which you never
need to open.
