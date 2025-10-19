# dyslexim/core/config.py
import json
import os
import sys

def get_asset_path(relative_path):
    """ Get absolute path to asset, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    return os.path.join(base_path, relative_path)

# Path to the config file
CONFIG_PATH = get_asset_path('config.json')

# Default values
DEFAULT_HIGHLIGHT_COLOR = "rgba(255, 200, 0, 0.35)"
DEFAULT_FONT = "OpenDyslexic"
DEFAULT_HIGHLIGHT_ALIGNMENT = "left"
POST_ONBOARDING_URL = "https://www.google.com"

def load_config():
    """Loads the configuration from config.json."""
    if not os.path.exists(CONFIG_PATH):
        return {
            'highlightColor': DEFAULT_HIGHLIGHT_COLOR,
            'onboarding_complete': False,
            'font': DEFAULT_FONT,
            'highlightAlignment': DEFAULT_HIGHLIGHT_ALIGNMENT
        }
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            'highlightColor': DEFAULT_HIGHLIGHT_COLOR,
            'onboarding_complete': False,
            'font': DEFAULT_FONT,
            'highlightAlignment': DEFAULT_HIGHLIGHT_ALIGNMENT
        }

def save_config(config):
    """Saves the configuration to config.json."""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError:
        pass

# Initial config load
config = load_config()

# URL to load in the initial tab
HOME_URL = "file:///" + get_asset_path('home.html').replace('\\', '/')
SETTINGS_URL = "file:///" + get_asset_path('settings.html').replace('\\', '/')

# Small delay in milliseconds before injecting the gaze handler after a page load
INJECT_DELAY_MS = 220

# Frequency of gaze updates in milliseconds (e.g., 100ms = 10Hz)
GAZE_UPDATE_INTERVAL_MS = 100