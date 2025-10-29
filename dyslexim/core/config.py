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
DEFAULT_FONT = "Poppins"
DEFAULT_HIGHLIGHT_ALIGNMENT = "center"
DEFAULT_READING_MASK = True
DEFAULT_TTS_HOVER_TIME = 1.0
POST_ONBOARDING_URL = "https://www.google.com"
DEFAULT_SEARCH_ENGINE = "Google"
SEARCH_ENGINES = {
    "Google": "https://www.google.com/search?q={}",
    "Bing": "https://www.bing.com/search?q={}",
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "Yahoo": "https://search.yahoo.com/search?p={}",
    "Brave": "https://search.brave.com/search?q={}"
}


def load_config():
    """Loads the configuration from config.json, updating the global config object."""
    global config
    if not os.path.exists(CONFIG_PATH):
        new_config = {
            'highlightColor': DEFAULT_HIGHLIGHT_COLOR,
            'onboarding_complete': False,
            'font': DEFAULT_FONT,
            'highlightAlignment': DEFAULT_HIGHLIGHT_ALIGNMENT,
            'readingMask': DEFAULT_READING_MASK,
            'ttsHoverTime': DEFAULT_TTS_HOVER_TIME,
            'searchEngine': DEFAULT_SEARCH_ENGINE
        }
    else:
        try:
            with open(CONFIG_PATH, 'r') as f:
                new_config = json.load(f)
                if 'readingMask' not in new_config:
                    new_config['readingMask'] = DEFAULT_READING_MASK
                if 'ttsHoverTime' not in new_config:
                    new_config['ttsHoverTime'] = DEFAULT_TTS_HOVER_TIME
                if 'searchEngine' not in new_config:
                    new_config['searchEngine'] = DEFAULT_SEARCH_ENGINE
        except (json.JSONDecodeError, IOError):
            new_config = {
                'highlightColor': DEFAULT_HIGHLIGHT_COLOR,
                'onboarding_complete': False,
                'font': DEFAULT_FONT,
                'highlightAlignment': DEFAULT_HIGHLIGHT_ALIGNMENT,
                'readingMask': DEFAULT_READING_MASK,
                'ttsHoverTime': DEFAULT_TTS_HOVER_TIME,
                'searchEngine': DEFAULT_SEARCH_ENGINE
            }
    
    config.clear()
    config.update(new_config)
    return config

def save_config(config_data):
    """Saves the configuration to config.json."""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=2)
    except IOError:
        pass

# Initial config load
config = {}
load_config()

# URL to load in the initial tab
HOME_URL = "file:///" + get_asset_path('home.html').replace('\\', '/')
SETTINGS_URL = "file:///" + get_asset_path('settings.html').replace('\\', '/')

# Small delay in milliseconds before injecting the gaze handler after a page load
INJECT_DELAY_MS = 220

# Frequency of gaze updates in milliseconds (e.g., 100ms = 10Hz)
GAZE_UPDATE_INTERVAL_MS = 100
