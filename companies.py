"""Companies we pull directly from their own job board.

Every slug here was verified to return a non-empty job list. A slug that goes stale returns
zero rows silently, so watch.py warns when a board comes back empty or unreachable.

To add a company: find the slug in their careers URL (boards.greenhouse.io/SLUG,
jobs.ashbyhq.com/SLUG, jobs.lever.co/SLUG), confirm it responds, then add one line.

Not reachable this way: Meta, Apple, Google, Microsoft, and the traditional banks
(JPMorgan, Goldman, Morgan Stanley, Citi, BofA) all run custom or Workday portals.
Those need their own adapters.
"""

# platform -> [(display name, board slug)]
ROSTER = {
    "greenhouse": [
        # AI / frontier
        ("Anthropic", "anthropic"),
        ("Scale AI", "scaleai"),
        ("Databricks", "databricks"),
        ("Figure AI", "figureai"),
        ("Glean", "gleanwork"),
        ("Together AI", "togetherai"),
        # Space / defense
        ("SpaceX", "spacex"),
        ("Anduril", "andurilindustries"),
        ("Epirus", "epirus"),
        ("Verkada", "verkada"),
        ("Samsara", "samsara"),
        # Quant / trading
        ("Jane Street", "janestreet"),
        ("IMC Trading", "imc"),
        ("Optiver", "optiverus"),
        ("Jump Trading", "jumptrading"),
        ("Virtu Financial", "virtu"),
        ("Flow Traders", "flowtraders"),
        ("Akuna Capital", "akunacapital"),
        # Fintech
        ("Stripe", "stripe"),
        ("Coinbase", "coinbase"),
        ("Block", "block"),
        ("Robinhood", "robinhood"),
        ("Affirm", "affirm"),
        ("Brex", "brex"),
        ("Chime", "chime"),
        ("Gusto", "gusto"),
        # Consumer / infra unicorns
        ("DoorDash", "doordashusa"),
        ("Airbnb", "airbnb"),
        ("Lyft", "lyft"),
        ("Instacart", "instacart"),
        ("Pinterest", "pinterest"),
        ("Reddit", "reddit"),
        ("Roblox", "roblox"),
        ("Discord", "discord"),
        ("Figma", "figma"),
        ("Datadog", "datadog"),
        ("Cloudflare", "cloudflare"),
        ("Twilio", "twilio"),
        ("Dropbox", "dropbox"),
        ("Vercel", "vercel"),
        ("Airtable", "airtable"),
    ],
    "ashby": [
        ("OpenAI", "openai"),
        ("Cohere", "cohere"),
        ("Perplexity", "perplexity"),
        ("Harvey", "harvey"),
        ("Abridge", "abridge"),
        ("Cursor", "cursor"),
        ("Sierra", "sierra"),
        ("ElevenLabs", "elevenlabs"),
        ("Saronic", "saronic"),
        ("Snowflake", "snowflake"),
        ("Notion", "notion"),
        ("Plaid", "plaid"),
        ("Linear", "linear"),
        ("Ramp", "ramp"),
    ],
    "lever": [
        ("Palantir", "palantir"),
        ("Shield AI", "shieldai"),
        ("Spotify", "spotify"),
    ],
    # Workday needs three values, not one: (tenant, wd number, site slug). None are guessable —
    # each was read off the company's careers page and confirmed to return a non-zero total.
    "workday": [
        ("NVIDIA", ("nvidia", 5, "NVIDIAExternalCareerSite")),
        ("Boeing", ("boeing", 1, "EXTERNAL_CAREERS")),
        ("Intel", ("intel", 1, "External")),
        ("Micron", ("micron", 1, "External")),
        ("Adobe", ("adobe", 5, "external_experienced")),
        ("Morgan Stanley", ("ms", 5, "External")),
        ("Citi", ("citi", 5, "2")),
        ("Capital One", ("capitalone", 12, "Capital_One")),
    ],
}
