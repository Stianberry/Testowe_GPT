from dotenv import load_dotenv

from .store import ROOT


def load_environment():
    # Desktop-only convenience: existing cloud bindings and exported values win.
    load_dotenv(ROOT / ".env", override=False)
