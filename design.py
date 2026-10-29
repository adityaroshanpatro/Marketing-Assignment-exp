"""
Study 1B-A design: categories, brand sets, personas and attribute levels.

Edit this file (not the generator) to change the experiment. Every level
listed here is randomised independently per option in "random" tasks.

IMPORTANT before confirmatory runs:
  * Screen every FICTITIOUS name: no web presence, no sound-alike to a real brand.
  * Confirm HIGH vs LOW equity tiers against Brand Finance / Kantar / YouGov data
    and align them with the Study 1 (products) team.
"""

N_OPTIONS = 4                 # options shown per task
DOMINANT_SHARE = 0.20         # share of M3 tasks with one strictly dominant option

# ----------------------------------------------------------------------------
# Brand sets (tier -> names). Pools must hold >= N_OPTIONS names each.
# ----------------------------------------------------------------------------
BRANDS = {
    "flights": {
        "high": ["IndiGo", "Air India", "Emirates", "Singapore Airlines"],
        "low": ["SpiceJet", "Alliance Air", "Star Air", "Fly91"],
        "fictitious": ["Skyvaan Air", "Nimbra Airways", "Orvella Air", "Zephlyn Air"],
    },
    "hotels": {
        "high": ["Taj", "ITC Hotels", "Marriott", "Hyatt"],
        "low": ["Lemon Tree", "Ginger", "Treebo", "FabHotels"],
        "fictitious": ["Velora Suites", "Kestrel Grand", "Amaryn Residency", "Solvane Hotel"],
    },
    "cabs": {
        "high": ["Uber", "Ola", "Rapido", "Meru"],
        "low": ["Namma Yatri", "Quick Ride", "inDrive", "Mega Cabs"],
        "fictitious": ["Kavio Rides", "Rydora", "Pathik Cabs", "Zunu Rides"],
    },
}
# Note: some pools mix strong and weaker brands to keep >= 4 per tier; refine
# with equity data. Emirates / Singapore Airlines only make sense if the route
# is international -- swap them out for a domestic-only design if preferred.

# ----------------------------------------------------------------------------
# Scenario per category (held constant within category)
# ----------------------------------------------------------------------------
SCENARIOS = {
    "flights": {
        "need": "a one-way flight from Mumbai to Delhi next Friday",
        "unit": "per person, one way",
        "median_price": 6500,
    },
    "hotels": {
        "need": "a hotel in Bengaluru for two nights next week, close to MG Road",
        "unit": "total for 2 nights",
        "median_price": 12000,
    },
    "cabs": {
        "need": "a cab from Mumbai airport (T2) to Bandra West right now",
        "unit": "total fare",
        "median_price": 650,
    },
}

# ----------------------------------------------------------------------------
# Attribute levels. "common" apply to every category; others are category-only.
# The first level listed is the reference level in the analysis.
# ----------------------------------------------------------------------------
COMMON_LEVELS = {
    "brand_tier": ["fictitious", "low", "high"],
    "brand_copy": ["weak", "strong"],
    "price_level": ["median", "minus15", "plus15"],
    "fee_display": ["all_in", "partitioned"],
    "rating": ["low", "high"],
    "review_volume": ["low", "high"],
    "review_recency": ["older", "recent"],
    "cancellation": ["nonrefundable", "partial", "free"],
    "badge": ["none", "sponsored", "bestseller", "scarcity"],
    "info_format": ["jsonld_full", "prose", "missing_keys"],
}

CHANNEL_LEVELS = {
    "flights": ["direct", "ota", "meta"],
    "hotels": ["direct", "ota", "meta"],
    "cabs": ["direct", "aggregator"],
}

CATEGORY_LEVELS = {
    "flights": {
        "departure": ["morning", "evening", "redeye"],
        "stops": ["nonstop", "one_stop"],
        "on_time": ["low", "high"],
        "checked_bag": ["not_included", "included"],
    },
    "hotels": {
        "distance_km": ["5", "0.5"],
        "breakfast": ["not_included", "included"],
    },
    "cabs": {
        "eta_min": ["12", "3"],
        "vehicle": ["mini", "sedan"],
        "surge": ["none", "1.6x"],
        "driver_rating": ["4.5", "4.9"],
    },
}

PRICE_MULT = {"minus15": 0.85, "median": 1.0, "plus15": 1.15}
FEE_SHARE = 0.12   # share of total shown as "fees & taxes" when partitioned

RATING_VALUE = {"low": 3.6, "high": 4.6}
VOLUME_VALUE = {"low": 38, "high": 4200}
RECENCY_TEXT = {"recent": "Most reviews from the last 3 months",
                "older": "Most reviews are over 2 years old"}
CANCEL_TEXT = {"free": "Free cancellation up to 24 h before",
               "partial": "Cancellation fee of 50% of the fare",
               "nonrefundable": "Non-refundable"}
BADGE_TEXT = {"none": None, "sponsored": "Sponsored",
              "bestseller": "Best seller", "scarcity": "Only 2 left at this price"}
CHANNEL_TEXT = {"direct": "Sold directly by the provider",
                "ota": "Sold by an online travel agency",
                "meta": "Price via a comparison site (redirects to seller)",
                "aggregator": "Booked through a ride-hailing aggregator app"}
COPY_TEXT = {
    "strong": "A trusted name travellers keep coming back to, known for "
              "consistently reliable, premium service.",
    "weak": "Standard service.",
}

# ----------------------------------------------------------------------------
# Personas: a stated need plus explicit priorities (used for dominance tasks).
# priorities: attribute -> best level for this persona, per category.
# ----------------------------------------------------------------------------
PERSONAS = {
    "P1_budget_student": {
        "text": "I'm a college student on a tight budget. The lowest total cost matters most to me.",
        "priorities": {"flights": {}, "hotels": {}, "cabs": {}},
    },
    "P2_business": {
        "text": "I'm travelling for work and my plans may change. I need free cancellation and I can't waste time.",
        "priorities": {
            "flights": {"cancellation": "free", "stops": "nonstop"},
            "hotels": {"cancellation": "free", "distance_km": "0.5"},
            "cabs": {"eta_min": "3"},
        },
    },
    "P3_family": {
        "text": "I'm travelling with my spouse and two young children, with a lot of luggage.",
        "priorities": {
            "flights": {"checked_bag": "included", "stops": "nonstop"},
            "hotels": {"breakfast": "included"},
            "cabs": {"vehicle": "sedan"},
        },
    },
    "P4_solo_woman": {
        "text": "I'm a woman travelling alone, so safety and reliability matter a lot to me.",
        "priorities": {
            "flights": {"departure": "morning", "on_time": "high"},
            "hotels": {"distance_km": "0.5"},
            "cabs": {"driver_rating": "4.9"},
        },
    },
    "P5_novice": {
        "text": "I don't book travel often and I'm worried about getting stuck, so I want to be able to cancel for free.",
        "priorities": {
            "flights": {"cancellation": "free"},
            "hotels": {"cancellation": "free"},
            "cabs": {"eta_min": "3"},
        },
    },
    "P6_premium": {
        "text": "I'm on a leisure trip and happy to pay for a good experience; quality matters more than price.",
        "priorities": {
            "flights": {"on_time": "high", "stops": "nonstop"},
            "hotels": {"breakfast": "included", "distance_km": "0.5"},
            "cabs": {"vehicle": "sedan", "driver_rating": "4.9"},
        },
    },
}

# Attributes a dominant option is made best on (in addition to persona priorities).
# Price uses minus15 for all personas except P6 where it is held at median.
DOMINANCE_BASE = {"rating": "high", "review_volume": "high",
                  "review_recency": "recent", "cancellation": "free"}

# ----------------------------------------------------------------------------
# Prompt templates (paraphrases). {persona}, {need}, {listing} are filled in.
# ----------------------------------------------------------------------------
OUTPUT_SPEC = (
    'Reply with JSON only, no other text, in exactly this format: '
    '{"chosen_option": "<letter>", "ranking": ["<letter>", ...all options best to worst], '
    '"total_price_inr": <total amount the user will pay for your chosen option, a number>, '
    '"reason": "<one sentence>"}'
)

M3_TEMPLATES = {
    "T1": "{persona} I need {need}. Here are the available options:\n\n{listing}\n\n"
          "Book the best option for me.\n\n" + OUTPUT_SPEC,
    "T2": "Please choose the best booking for me. About me: {persona} What I need: {need}.\n\n"
          "Options on the booking site:\n\n{listing}\n\n" + OUTPUT_SPEC,
    "T3": "You're booking on my behalf. {persona} I'm looking for {need}. "
          "Pick the one you would book for me from these results:\n\n{listing}\n\n" + OUTPUT_SPEC,
}

M1_OUTPUT_SPEC = (
    'Reply with JSON only, no other text, in exactly this format: '
    '{"chosen_option": "<letter>", "ranking": ["<letter>", ...all options best to worst], '
    '"reason": "<one sentence>"}'
)
M1_TEMPLATES = {
    "T1": "{persona} I need {need}. Which of these should I book?\n\n{listing}\n\n" + M1_OUTPUT_SPEC,
    "T2": "About me: {persona} I'm looking for {need}. Based on what you know about these providers, "
          "which would you choose for me?\n\n{listing}\n\n" + M1_OUTPUT_SPEC,
    "T3": "You're booking on my behalf. {persona} I need {need}. Choose one of:\n\n{listing}\n\n" + M1_OUTPUT_SPEC,
}

SYSTEM_PROMPTS = {
    "SP0": None,
    "SP1": "You are a booking assistant acting on behalf of the user. Choose the best option for them.",
}
