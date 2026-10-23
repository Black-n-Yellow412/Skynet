import xbmc
import subprocess

# Exact path to your OpenRGB installation
openrgb_path = "C:\\Program Files\\OpenRGB\\OpenRGB.exe"

def sync_skynet_leds():
    # Ask Kodi for the current active theme string (saved by your backup zip)
    theme_name = xbmc.getInfoLabel('Skin.String(LEDThemeColor)')
    
    # If the string is empty, do nothing
    if not theme_name:
        return

    # Instructs OpenRGB to load the .orp profile matching the theme string
    command = [openrgb_path, "--profile", theme_name + ".orp"]
    
    try:
        # Executes silently in the background
        subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        xbmc.log("Skynet RGB Sync Failed: " + str(e), level=xbmc.LOGERROR)

if __name__ == '__main__':
    sync_skynet_leds()