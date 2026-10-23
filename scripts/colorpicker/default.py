#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import xbmc, xbmcgui, xbmcaddon
import resources.lib.ColorPicker as cp

ADDON_ID = "script.skynet.colorpicker"
try:
    ADDON = xbmcaddon.Addon(ADDON_ID)
    ADDON_PATH = ADDON.getAddonInfo('path')
except Exception:
    ADDON = None
    ADDON_PATH = SCRIPT_DIR

MONITOR = xbmc.Monitor()

class Main(object):
    def __init__(self):
        params = self.get_params()
        if params:
            # SCRIPT_DIR provides the fallback path for resources/skins/Default/1080i/
            color_picker = cp.ColorPicker("script-skin_helper_service-ColorPicker.xml", SCRIPT_DIR, "Default", "1080i")
            
            # Map the 'setting' parameter from our XML directly to the 'SKINSTRING' the engine expects
            color_picker.skinstring = params.get("SETTING", params.get("SKINSTRING", ""))
            color_picker.win_property = params.get("WINPROPERTY", "")
            color_picker.active_palette = params.get("PALETTE", "")
            color_picker.header_label = params.get("HEADER", "")
            
            propname = params.get("SHORTCUTPROPERTY", "")
            color_picker.shortcut_property = propname
            
            color_picker.doModal()

            if propname and not isinstance(color_picker.result, int):
                self.wait_for_skinshortcuts_window()
                xbmc.sleep(400)
                current_window = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
                current_window.setProperty("customProperty", propname)
                current_window.setProperty("customValue", color_picker.result[0])
                xbmc.executebuiltin("SendClick(404)")
                xbmc.sleep(250)
                current_window.setProperty("customProperty", "%s.name" % propname)
                current_window.setProperty("customValue", color_picker.result[1])
                xbmc.executebuiltin("SendClick(404)")
            del color_picker

    @staticmethod
    def get_params():
        params = {}
        for arg in sys.argv:
            if not arg or arg == ADDON_ID or arg == 'default.py' or arg.endswith('.py'):
                continue
            elif "=" in arg:
                paramname = arg.split('=')[0]
                paramvalue = arg.replace(paramname + "=", "")
                params[paramname] = paramvalue
                params[paramname.upper()] = paramvalue
        return params

    @staticmethod
    def wait_for_skinshortcuts_window():
        while not MONITOR.abortRequested() and not xbmc.getCondVisibility("Window.IsActive(DialogSelect.xml) | Window.IsActive(script-skin_helper_service-ColorPicker.xml) | Window.IsActive(DialogKeyboard.xml)"):
            MONITOR.waitForAbort(0.1)

if __name__ == "__main__":
    Main()
