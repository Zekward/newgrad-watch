"""Companies we pull directly from their own job board.

Every slug here was verified to return a non-empty list. A slug that goes stale returns
zero rows silently, which is why watch.py warns when a source comes back empty.
"""

# platform -> [(display name, board slug)]
ROSTER = {
    "greenhouse": [
        ("Anthropic", "anthropic"),
        ("SpaceX", "spacex"),
        ("Anduril", "andurilindustries"),
        ("Scale AI", "scaleai"),
        ("Databricks", "databricks"),
        ("Figure AI", "figureai"),
        ("Stripe", "stripe"),
        ("Coinbase", "coinbase"),
    ],
    "ashby": [
        ("OpenAI", "openai"),
        ("Cursor", "cursor"),
        ("Ramp", "ramp"),
        ("Sierra", "sierra"),
        ("ElevenLabs", "elevenlabs"),
    ],
    "lever": [
        ("Palantir", "palantir"),
    ],
}
