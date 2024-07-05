from PySide6.QtCore import QObject, Signal, Slot
from pathlib import Path
import shutil
import winreg
import os
import subprocess
import urllib.request


class SystemController(QObject):
    """Signals"""
    maya_checked = Signal(bool)
    git_checked = Signal(bool)
    git_installed = Signal(bool)
    log_message = Signal(str)
    error_message = Signal(str)
    setup_finished = Signal()

    maya_paths = [
        "C://Program Files/Autodesk/Maya2022/bin/maya.exe",
        "C://Program Files/Autodesk/Maya2024/bin/maya.exe",
        "C://Program Files/Autodesk/Maya2025/bin/maya.exe"
    ]
    maya_bin = ""

    def __init__(self, config):
        super(SystemController, self).__init__()
        self.config = config
        self.git_path = config["general"]["git_path"]
        self.git_installer_url = config["general"]["git_installer_url"]
        self.git_token = config["git"]["personal_access_token"]
        self.git_api_url = config["git"]["gitlab_api_url"]
        self.git_user = config["git"]["username"]
        self.maya_installed = False

    def setup(self):
        self._check_for_maya()
        if not self._check_for_git():
            self.install_git()
        self.setup_finished.emit()

    def _check_for_maya(self):
        for path in self.maya_paths:
            if Path(path).exists():
                self.maya_bin = path
                self.maya_installed = True
                self.maya_checked.emit(True)

        self.maya_checked.emit(True)

    def _check_for_git(self) -> bool:
        # Check if 'git' is in the system PATH
        if shutil.which("git"):
            self.git_checked.emit(True)
            return True

        # Check the registry
        registry_paths = [
            r"SOFTWARE\GitForWindows",
            r"SOFTWARE\WOW6432Node\GitForWindows"
        ]

        def check_registry_key(hkey, path):
            try:
                reg_key = winreg.OpenKey(hkey, path)
                winreg.CloseKey(reg_key)
                self.git_checked.emit(True)
                return True
            except FileNotFoundError:
                pass
            self.git_checked.emit(True)
            return False

        for path in registry_paths:
            if check_registry_key(winreg.HKEY_LOCAL_MACHINE, path):
                self.git_checked.emit(True)
                return True
        self.git_checked.emit(False)
        return False

    def download_git_installer(self, url, save_path):
        try:
            self.log_message.emit(f"Downloading Git installer from {url}...")
            urllib.request.urlretrieve(url, save_path)
            self.log_message.emit("Download completed.")
        except Exception as e:
            self.error_message.emit(f"Error downloading Git installer: {e}")
            return False
        return True

    def run_git_installer(self, installer_path):
        try:
            self.log_message.emit(f"Running Git installer: {installer_path}")
            # Run the installer silently with default options
            subprocess.run([installer_path, '/SILENT'], check=True)
            self.log_message.emit("Git installation completed.")
        except subprocess.CalledProcessError as e:
            self.log_message.emit(f"Error during Git installation: {e}")
            return False
        return True

    def install_git(self):
        self.log_message.emit("Git wasn't found in the system, Start Installing git")
        installer_path = os.path.join(os.getcwd(), "git_installer.exe")

        # Download the Git installer
        if not self.download_git_installer(self.git_installer_url, installer_path):
            self.git_installed.emit(False)
            return False

        # Run the Git installer
        if self.run_git_installer(installer_path):
            self.log_message.emit("Git successfully installed.")
            self.git_installed.emit(True)
        else:
            self.git_installed.emit(False)
            self.log_message.emit("Git installation failed.")

        # Clean up by removing the installer
        try:
            os.remove(installer_path)
            self.log_message.emit("Installer removed.")
        except OSError as e:
            self.error_message.emit(f"Error removing installer: {e}")

    @Slot()
    def open_maya(self):
        if not self.maya_installed:
            return
        self.log_message.emit("Opening Maya...")
        result = subprocess.run([self.maya_bin])

        self.log_message.emit(result.stdout)
        if result.stderr:
            self.error_message.emit(result.stderr)
