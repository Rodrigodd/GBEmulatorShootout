from util import *
from emulator import Emulator
from test import *
import time
import os
import shutil

def wsl(command, *, cwd=None):
    return subprocess.Popen([
        "wsl.exe", "-d", "Debian", "--",
        "bash", "-xc",
        command,
    ], cwd=cwd)

class JitBoy(Emulator):
    def __init__(self):
        super().__init__("JitBoy", "https://github.com/sysprog21/jitboy", startup_time=4.5)
        self.title_check = lambda title: title.startswith('load') or title.startswith('jitboy')
    
    def setup(self):
        if os.path.exists('emu/jitboy/jitboy'):
            return

        if not os.path.exists('downloads/jitboy'):
            os.system("git clone --depth=1 http://github.com/sysprog21/jitboy.git downloads/jitboy")
            os.system("cd downloads\\jitboy && git apply ..\\..\\emulators\\jitboy.patch")

        # requires: libsdl2-dev make
        wsl('export GIT_SSL_NO_VERIFY=true; make clean; make build/jitboy', cwd="downloads/jitboy").wait()
        os.makedirs("emu/jitboy", exist_ok=True)
        shutil.copyfile("downloads/jitboy/build/jitboy", "emu/jitboy/jitboy")

    def startProcess(self, rom, *, model, required_features):
        if model != DMG:
            return None
        
        rom = rom.replace("\\", "/")

        # Renders the emulator in Xvfb (a X11 server that just renders to a frame buffer)
        p = wsl(f'Xvfb :43 -screen 0 480x432x24 & trap \'jobs -p | xargs kill\' EXIT TERM INT; DISPLAY=:43 ./jitboy "../../{rom}"', cwd="emu/jitboy")

        self.start_time = time.monotonic()

        return p

    def endProcess(self, p: subprocess.Popen):
        wsl('DISPLAY=:43 xdotool search "jitboy" windowclose')
        p.wait()

    def isWindowOpen(self):
        time.sleep(1.0 - (time.monotonic() - self.start_time))
        return True

    def getScreenshot(self):
        # Dump the content of the X11 Server root window to a file, and convert it to PNG.
        wsl(f'xwd -root -display :43 | convert xwd:- png:- > tmp.png').wait()

        # The tmp.png could be corrupted if the command above fails for some reason
        try:
            screenshot = PIL.Image.open("tmp.png", formats=["PNG"])

            x = (screenshot.size[0] - 160*3) // 2
            y = (screenshot.size[1] - 144*3) // 2
            screenshot = screenshot.crop((x, y, x + 160*3, y + 144*3))
            screenshot = screenshot.resize((160, 144))

            screenshot.save('tmp2.png')
        except Exception as e:
            print(e)
            return None

        return screenshot
