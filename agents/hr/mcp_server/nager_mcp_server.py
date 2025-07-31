import requests
import logging
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("holiday_server.log"),
        logging.StreamHandler()
    ]
)

# Create a logger specific to this application
logger = logging.getLogger("holiday_server")

# Create the MCP server instance
mcp = FastMCP("Public Holiday Server")
logger.info("Initialized Public Holiday Server")

# Define the tool
@mcp.tool()
def get_public_holidays(
    year: int = Field(2025, description="Year for which to fetch holidays (defaults to 2025)"),
    country_code: str = Field("US", description="ISO 3166-1 alpha-2 code (defaults to 'US')")
) -> dict:
    """
    Proxy to Nager.Date PublicHolidays API.
    Returns:
      {
        "summary": str,      # e.g. "11 holidays: 2025-01-01 (New Year's Day), 2025-01-20 (Martin Luther King Jr. Day), …"
        "count": int         # e.g. 11
      }
    """
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    resp = requests.get(url)
    resp.raise_for_status()

    raw = resp.json()  # full list of holiday objects
    count = len(raw)
    logger.info(f"Fetched {count} holidays for {country_code} in {year}")

    # build a summary of "date (localName)" entries
    entries = [f"{item['date']} ({item['localName']})" for item in raw]
    summary = f"{count} holidays: " + ", ".join(entries)
    return {"summary": summary, "count": count}


if __name__ == "__main__":
    logger.info("Starting Public Holiday Server with stdio transport")
    try:
        mcp.run(transport='stdio')
        logger.info("Server shutting down normally")
    except Exception as e:
        logger.critical(f"Server crashed with error: {e}", exc_info=True)
        raise
