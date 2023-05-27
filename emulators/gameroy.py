from util import *
from emulator import Emulator
from test import *
import shutil
import os


class GameRoy(Emulator):
    def __init__(self):
        super().__init__("gameroy", "https://github.com/Rodrigodd/gameroy", startup_time=0.8, features=None)
        self.title_check = lambda title: title.endswith('gameroy')
        self.speed = 15.0

    def setup(self):
        downloadGithubRelease("Rodrigodd/gameroy", "downloads/gameroy.zip")
        extract("downloads/gameroy.zip", "emu/gameroy")
        setDPIScaling("emu/gameroy/gameroy.exe")
        os.system('mklink emu/gameroy/opengl32.dll "downloads/mesa/x64/opengl32.dll"')
        os.system('mklink emu/gameroy/libglapi.dll "downloads/mesa/x64/libglapi.dll"')
    
    def startProcess(self, rom, *, model, required_features):
        if model != DMG:
            return None
        return subprocess.Popen([
            "emu/gameroy/gameroy.exe",
            "--screen-size", "160x144",
            "--frame-skip",
            os.path.abspath(rom),
        ], cwd="emu/gameroy")
