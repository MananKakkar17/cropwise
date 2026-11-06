"""Indian states, cities, and seasonal crop tips for location-based advisory."""

from __future__ import annotations

INDIAN_LOCATIONS: dict[str, list[str]] = {
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad"],
    "Karnataka": ["Bengaluru", "Mysuru", "Hubballi", "Belagavi", "Mangaluru"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Prayagraj"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer"],
    "West Bengal": ["Kolkata", "Siliguri", "Durgapur", "Asansol", "Howrah"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Nellore"],
    "Telangana": ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad", "Khammam"],
    "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Karnal"],
}

SEASONAL_TIPS: dict[str, str] = {
    "Maharashtra": "Kharif (Jun–Sep): rice, cotton, soybean. Rabi (Oct–Mar): wheat, gram, jowar.",
    "Karnataka": "Monsoon suits rice and ragi. Winter is good for sunflower and chickpea.",
    "Tamil Nadu": "Three-season farming: kuruvai rice (Jun), samba rice (Aug), thaladi (Dec).",
    "Uttar Pradesh": "Rabi wheat and mustard dominate. Kharif rice and sugarcane in eastern UP.",
    "Punjab": "Wheat–rice rotation is common. Plan wheat sowing in November.",
    "Gujarat": "Groundnut and cotton in kharif; wheat and cumin in rabi.",
    "Rajasthan": "Bajra and moong in kharif; mustard and wheat in rabi with irrigation.",
    "West Bengal": "Aman rice after monsoon; Boro rice in winter with irrigation.",
    "Andhra Pradesh": "Kharif rice and cotton; rabi maize and pulses.",
    "Telangana": "Cotton and maize in kharif; chickpea and safflower in rabi.",
    "Kerala": "Year-round coconut and spices; rice in monsoon paddies.",
    "Madhya Pradesh": "Soybean and maize in kharif; wheat and gram in rabi.",
    "Bihar": "Rice in kharif; wheat and maize in rabi across the Gangetic plain.",
    "Odisha": "Kharif rice is primary; rabi pulses and oilseeds on residual moisture.",
    "Haryana": "Wheat–mustard–rice rotation; plan irrigation for rabi crops.",
}


def normalise_city(city: str) -> str:
    """Strip state suffixes so OpenWeather queries resolve correctly."""
    cleaned = city.strip()
    if "," in cleaned:
        cleaned = cleaned.split(",")[0].strip()
    return cleaned
