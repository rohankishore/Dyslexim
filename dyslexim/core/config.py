# dyslexim/core/config.py
import json
import os

# Path to the config file
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

# Default values
DEFAULT_HIGHLIGHT_COLOR = "rgba(255, 200, 0, 0.35)"
DEFAULT_FONT = "Poppins"
DEFAULT_HIGHLIGHT_ALIGNMENT = "center"
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
HOME_URL = "file:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), 'home.html').replace('\\', '/')

# Small delay in milliseconds before injecting the gaze handler after a page load
INJECT_DELAY_MS = 220

# Frequency of gaze updates in milliseconds (e.g., 50ms = 20Hz)
GAZE_UPDATE_INTERVAL_MS = 50
