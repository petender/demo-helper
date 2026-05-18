import os

from dotenv import load_dotenv

load_dotenv()

RUNWAYML_API_SECRET = os.environ.get("RUNWAYML_API_SECRET", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get(
	"OPENAI_BASE_URL",
	"https://pdtopenai.openai.azure.com/",
)

DEFAULT_MODEL = "gen4.5"
DEFAULT_RATIO = "1280:720"
DEFAULT_DURATION = 6
POLL_INTERVAL = 5  # seconds between task status checks
OUTPUT_DIR = "output"
