import pyautogui
import requests
import os
import zipfile
import subprocess
import time
import PIL.Image
import PIL.ImageChops
import sys
import argparse
import json
import traceback
from emulator import Emulator

import testroms.blarg
import testroms.mooneye
import testroms.acid
import testroms.samesuite
import testroms.ax6
import testroms.daid
import testroms.hacktix
import testroms.cpp
from emulators.kigb import KiGB
from emulators.bgb import BGB
from emulators.vba import VBA, VBAM
from emulators.mgba import MGBA
from emulators.sameboy import SameBoy
from emulators.nocash import NoCash
from emulators.gambatte import GambatteSpeedrun
from emulators.emulicious import Emulicious
from emulators.bdm import BDM
from emulators.higan import Higan
from emulators.goomba import Goomba
from emulators.binjgb import Binjgb
from emulators.pyboy import PyBoy
from emulators.ares import Ares
from emulators.emmy import Emmy
from util import *
from test import *

from emulators.gameroy import GameRoy
from emulators.jitboy import JitBoy


emulators: list[Emulator] = [
    Emulicious(),
    JitBoy(),
    GameRoy(),
    BDM(),
    MGBA(), # Black screen on github actions
    KiGB(), # Crashes on github actions
    SameBoy(),
    BGB(),
    VBA(),
    VBAM(),
    NoCash(),
    GambatteSpeedrun(),
    # Higan(), # Crashes all over the place.
    Goomba(),
    Binjgb(),
    PyBoy(),
    Ares(),
    Emmy(),
]
tests = testroms.acid.all + testroms.blarg.all + testroms.daid.all + testroms.ax6.all + testroms.mooneye.all + testroms.samesuite.all + testroms.hacktix.all + testroms.cpp.all

def checkFilter(input, filter_data):
    if filter_data is None:
        return True
    input = str(input)

    # if there is at least one !QUERY, any emulator not int the negative query
    # will be accepted
    out_filter = False
    for f in filter_data:
        if f.startswith("!"):
            out_filter = True
            if f[1:] in input:
                return False
    if out_filter:
        return True

    # if there are not !QUERY, any emulator matching a query in be included,
    # remaining will be filtered out.
    for f in filter_data:
        if not f.startswith("!"):
            if f in input:
                return True
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='append', help="Filter for tests with keywords")
    parser.add_argument('--emulator', action='append', help="Filter to test only emulators with keywords")
    parser.add_argument('--model', action='append', help="Filter to tests with model")
    parser.add_argument('--get-runtime', action='store_true')
    parser.add_argument('--get-startuptime', action='store_true')
    parser.add_argument('--dump-emulators-json', action='store_true')
    parser.add_argument('--dump-tests-json', action='store_true')
    args = parser.parse_args()

    for model in args.model or []:
        if model not in ["DMG", "CGB", "SGB"]:
            print("Model %s is invalid. Only DMG, CGB and SGB are valid models")
            exit(1)

    tests = [
        test
        for test in tests
        if checkFilter(test, args.test) and checkFilter(test.model, args.model)
    ]
    emulators = [emulator for emulator in emulators if checkFilter(emulator, args.emulator)]

    print("%d emulators" % (len(emulators)))
    print("%d tests" % (len(tests)))

    if args.get_runtime:
        for emulator in emulators:
            emulator.setup()
            for test in tests:
                if not checkFilter(test, args.test):
                    continue
                print("%s: %s: %g seconds" % (emulator, test, emulator.getRunTimeFor(test)))
            emulator.undoSetup()
        sys.exit()
    if args.dump_emulators_json:
        json.dump({
            str(emulator): {
                "file": emulator.getJsonFilename(),
                "url": emulator.url,
            } for emulator in emulators
        }, open("emulators.json", "wt"), indent="  ")
    if args.dump_tests_json:
        json.dump([
            {
                'name': str(test),
                'description': test.description,
                'url': test.url,
            } for test in tests
        ], open("tests.json", "wt"), indent="  ")
    if args.dump_tests_json or args.dump_emulators_json:
        sys.exit()

    if args.get_startuptime:
        f = open("startuptime.html", "wt")
        f.write("<html><body>\n")
        for emulator in emulators:
            try:
                emulator.setup()
                dmg_start_time, dmg_screenshot = emulator.measureStartupTime(model=DMG)
                gbc_start_time, gbc_screenshot = emulator.measureStartupTime(model=CGB)
                sgb_start_time, sgb_screenshot = emulator.measureStartupTime(model=SGB)
                if dmg_screenshot is not None:
                    print("Startup time: %s = %g (dmg)" % (emulator, dmg_start_time or 0.0))
                    f.write("%s (dmg)<br>\n<img src='data:image/png;base64,%s'><br>\n" % (emulator, imageToBase64(dmg_screenshot)))
                if gbc_screenshot is not None:
                    print("Startup time: %s = %g (gbc)" % (emulator, gbc_start_time or 0.0))
                    f.write("%s (gbc)<br>\n<img src='data:image/png;base64,%s'><br>\n" % (emulator, imageToBase64(gbc_screenshot)))
                if sgb_screenshot is not None:
                    print("Startup time: %s = %g (sgb)" % (emulator, sgb_start_time or 0.0))
                    f.write("%s (sgb)<br>\n<img src='data:image/png;base64,%s'><br>\n" % (emulator, imageToBase64(sgb_screenshot)))
                emulator.undoSetup()
            except Exception as e:
                print(f'Exception while running {emulator}')
                traceback.print_exc()
                f.write("%s (sgb)<br>\n%s<br>\n" % (emulator, traceback.format_exc()))

        f.write("</body></html>")
        sys.exit()

    results = {}
    for emulator in emulators:
        results[emulator] = {}
        try:
            emulator.setup()
        except Exception:
            print(f'Exception while running {emulator}')
            traceback.print_exc()
            continue

        for test in tests:
            skip = False
            for feature in test.required_features:
                if feature not in emulator.features:
                    skip = True
                    print("Skipping %s on %s because of missing feature %s" % (test, emulator, feature))
            if not skip:
                try:
                    result = emulator.run(test)
                    if result is not None:
                        results[emulator][test] = result
                except KeyboardInterrupt:
                    exit(0)
                except:
                    print("Emulator %s failed to run properly" % (emulator))
                    traceback.print_exc()
        emulator.undoSetup()
    emulators.sort(key=lambda emulator: len([result[0] for result in results[emulator].values() if result.result != "FAIL"]), reverse=True)

    for emulator in emulators:
        data = {
            'emulator': str(emulator),
            'date': time.time(),
            'tests': {str(test): {'result': result.result, 'startuptime': result.startuptime, 'runtime': result.runtime, 'screenshot': imageToBase64(result.screenshot)} for test, result in results[emulator].items()},
        }
        if results[emulator]:
            json.dump(data, open(emulator.getJsonFilename(), "wt"), indent="  ")
