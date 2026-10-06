Prospero Companion on a Mac - start here

1. Double-click install.command once. It finds or installs Python and Node.js, then sets everything up.
   The first time, macOS may refuse to open it; Program/docs/macos.md shows how to allow it.
2. Double-click launch.command to start the Companion. It opens in your browser at http://127.0.0.1:8775.
   Keep its Terminal window open while you use it; close the window to stop.

Other scripts in this folder:
  update.command           Gets the latest version and reinstalls. Close the Companion first.
  status.command           Says whether the Companion is running.
  stop.command             Stops the Companion if you lost its window.
  create-shortcut.command  Puts a Prospero Companion app in your Applications folder.
  dev.command              Development mode, for working on the code.

Your companion's data is not in this folder. It lives in ~/Library/Application Support/ProsperoCompanion,
so updating or re-downloading the program keeps it. The app itself is in the Program folder,
which you never need to open.
