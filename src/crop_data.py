"""Crop calendar, planting windows, and fertilizer product mapping."""

from __future__ import annotations

CROP_CALENDAR: dict[str, dict[str, str]] = {
    "Rice": {
        "sowing": "Jun – Jul (Kharif) or Nov – Dec (Rabi)",
        "harvest": "Oct – Nov or Apr – May",
        "tip": "Needs standing water or reliable irrigation during tillering.",
    },
    "Maize": {
        "sowing": "Jun – Jul or Jan – Feb",
        "harvest": "Sep – Oct or Apr – May",
        "tip": "Use well-drained fields; apply nitrogen in split doses.",
    },
    "Cotton": {
        "sowing": "May – Jun",
        "harvest": "Oct – Dec",
        "tip": "Warm season crop; monitor for bollworm after flowering.",
    },
    "Wheat": {
        "sowing": "Nov – Dec",
        "harvest": "Mar – Apr",
        "tip": "Cool-season crop; ensure timely sowing before winter peak.",
    },
    "Jute": {
        "sowing": "Mar – Apr",
        "harvest": "Jul – Aug",
        "tip": "Requires high rainfall and humid conditions.",
    },
    "Sugarcane": {
        "sowing": "Oct – Nov or Feb – Mar",
        "harvest": "12–18 months after planting",
        "tip": "Long-duration crop; needs deep, fertile soil with irrigation.",
    },
    "Groundnut": {
        "sowing": "Jun – Jul",
        "harvest": "Sep – Oct",
        "tip": "Well-drained sandy loam; avoid waterlogging.",
    },
    "Chickpea": {
        "sowing": "Oct – Nov",
        "harvest": "Feb – Mar",
        "tip": "Rabi pulse; inoculate seeds for better nitrogen fixation.",
    },
    "Soybean": {
        "sowing": "Jun – Jul",
        "harvest": "Sep – Oct",
        "tip": "Kharif oilseed; sensitive to waterlogging at germination.",
    },
    "Banana": {
        "sowing": "Year-round (plant suckers)",
        "harvest": "12–15 months",
        "tip": "Requires consistent moisture and organic matter.",
    },
    "Mango": {
        "sowing": "Plant grafts Jun – Aug",
        "harvest": "Apr – Jun (fruiting)",
        "tip": "Perennial; flowering needs dry winter months.",
    },
    "Pomegranate": {
        "sowing": "Plant cuttings Jul – Aug",
        "harvest": "Aug – Jan",
        "tip": "Drought-tolerant once established; prefers semi-arid climate.",
    },
}

DEFAULT_CALENDAR = {
    "sowing": "Check local agricultural calendar",
    "harvest": "Varies by region and irrigation",
    "tip": "Confirm sowing dates with your local Krishi Vigyan Kendra (KVK).",
}

FERTILIZER_PRODUCTS: dict[str, str] = {
    "nitrogen": "urea",
    "phosphorus": "npk-19",
    "potassium": "npk-19",
    "balanced": "npk-19",
    "organic": "compost",
}

ORDER_STATUSES = [
    "Order confirmed",
    "Packed",
    "Shipped",
    "Out for delivery",
    "Delivered",
]
