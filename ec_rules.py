"""
Environmental Clearance (EC) 18 Statutory Appraisal Rules.
Defines standard compliance evaluation parameters aligned with MoEFCC EIA Notification (2006)
and EAC/SEAC statutory scrutiny guidelines.
"""
from typing import List, Dict, Any, Literal

EC_RULES: List[Dict[str, Any]] = [
    {
        "id": "EC-R01",
        "name": "Terms of Reference (ToR) Compliance",
        "category": "Critical",
        "weight": 3,
        "description": "Full conformity with ministry-approved standard and specific Terms of Reference (ToR) conditions.",
        "keywords": ["terms of reference", "tor compliance", "standard tor", "specific tor", "ministry letter", "tor conditions"]
    },
    {
        "id": "EC-R02",
        "name": "Baseline Ambient Air Quality (AAQ)",
        "category": "Critical",
        "weight": 3,
        "description": "Valid one-season non-monsoon baseline monitoring for PM10, PM2.5, SO2, NOx across core and buffer zones.",
        "keywords": ["ambient air quality", "aaqm", "pm10", "pm2.5", "so2", "nox", "baseline air monitoring", "air quality stations"]
    },
    {
        "id": "EC-R03",
        "name": "Water Balance & CGWA Groundwater NOC",
        "category": "Critical",
        "weight": 3,
        "description": "Daily freshwater demand quantification and Central Ground Water Authority (CGWA) abstraction permission.",
        "keywords": ["water balance", "cgwa", "groundwater noc", "freshwater intake", "daily water requirement", "abstraction permission"]
    },
    {
        "id": "EC-R04",
        "name": "Effluent & Zero Liquid Discharge (ZLD)",
        "category": "Critical",
        "weight": 3,
        "description": "Industrial trade effluent treatment plant (ETP/STP) design, recycling ratio, and ZLD discharge norms.",
        "keywords": ["zero liquid discharge", "zld", "etp", "stp", "effluent treatment", "treated effluent", "trade effluent"]
    },
    {
        "id": "EC-R05",
        "name": "Eco-Sensitive Zone (ESZ) & Wildlife Clearance",
        "category": "Critical",
        "weight": 3,
        "description": "Clearance and buffer assessment for National Parks, Wildlife Sanctuaries, or ESZ within 10 km radius.",
        "keywords": ["eco-sensitive zone", "esz", "wildlife sanctuary", "national park", "10 km", "nbwl", "wildlife clearance", "forest clearance"]
    },
    {
        "id": "EC-R06",
        "name": "Public Consultation & Hearing Proceedings",
        "category": "Critical",
        "weight": 3,
        "description": "SPCB Public Hearing minutes, attendance records, public grievances raised, and itemized budgeted action plan.",
        "keywords": ["public hearing", "public consultation", "spcb hearing", "minutes of hearing", "action plan", "grievances"]
    },
    {
        "id": "EC-R07",
        "name": "Baseline Water Quality Assessment",
        "category": "Major",
        "weight": 2,
        "description": "Seasonal baseline sampling data for ground and surface water bodies against IS:10500 / CPCB criteria.",
        "keywords": ["water quality", "surface water sampling", "groundwater quality", "bod", "cod", "tds", "heavy metals", "is 10500"]
    },
    {
        "id": "EC-R08",
        "name": "Baseline Ambient Noise Survey",
        "category": "Major",
        "weight": 2,
        "description": "Day and night ambient noise monitoring across core/buffer receptors vs statutory CPCB decibel limits.",
        "keywords": ["ambient noise", "noise monitoring", "levent", "day and night noise", "decibel", "db(a)", "cpcb noise norms"]
    },
    {
        "id": "EC-R09",
        "name": "Terrestrial & Aquatic Ecological Survey",
        "category": "Major",
        "weight": 2,
        "description": "Comprehensive flora/fauna ecological inventory and conservation plan for Schedule-I endangered species.",
        "keywords": ["flora and fauna", "biodiversity survey", "schedule-i", "endangered species", "conservation plan", "ecological assessment"]
    },
    {
        "id": "EC-R10",
        "name": "Air Dispersion Modeling & Stack Heights",
        "category": "Major",
        "weight": 2,
        "description": "AERMOD/ISCST3 dispersion modeling with calculated stack heights, plume rise, and maximum ground level concentrations.",
        "keywords": ["dispersion modeling", "aermod", "stack height", "stack emission", "glc", "ground level concentration", "boiler stack"]
    },
    {
        "id": "EC-R11",
        "name": "Hazardous & Solid Waste Management",
        "category": "Major",
        "weight": 2,
        "description": "Hazardous waste inventory, storage shed design, authorized recyclers tie-up, and TSDF disposal agreements.",
        "keywords": ["hazardous waste", "tsdf", "solid waste", "e-waste", "waste storage", "recyclers", "authorization", "hw rules"]
    },
    {
        "id": "EC-R12",
        "name": "Greenbelt Development Plan (33% Area)",
        "category": "Major",
        "weight": 2,
        "description": "Minimum 33% plant layout area designated for greenbelt plantation with native species and canopy density.",
        "keywords": ["greenbelt", "green belt", "33%", "plantation", "native species", "tree density", "afforestation"]
    },
    {
        "id": "EC-R13",
        "name": "Environmental Management Plan (EMP) Budget",
        "category": "Major",
        "weight": 2,
        "description": "Comprehensive EMP with separate capital expenditure (CAPEX) and annual recurring (OPEX) financial provisions.",
        "keywords": ["emp budget", "capital cost", "recurring cost", "environmental management plan", "capex", "opex", "financial allocation"]
    },
    {
        "id": "EC-R14",
        "name": "Disaster Management & Onsite Emergency Plan",
        "category": "Major",
        "weight": 2,
        "description": "Quantitative Risk Assessment (QRA), hazard consequence analysis, toxic release modeling, and emergency response.",
        "keywords": ["disaster management", "dmp", "onsite emergency", "offsite emergency", "risk assessment", "qra", "hazard identification"]
    },
    {
        "id": "EC-R15",
        "name": "Land Use & Layout Demarcation",
        "category": "Minor",
        "weight": 1,
        "description": "Topographical survey, 500m buffer land-use classification, plant layout coordinates, and land acquisition status.",
        "keywords": ["land use", "lulc", "topography", "geo-coordinates", "layout plan", "land acquisition", "buffer zone"]
    },
    {
        "id": "EC-R16",
        "name": "Soil Quality & Baseline Fertility Survey",
        "category": "Minor",
        "weight": 1,
        "description": "Representative soil core profile testing assessing permeability, organic carbon, fertility, and heavy metal concentrations.",
        "keywords": ["soil quality", "soil sampling", "permeability", "organic carbon", "soil fertility", "soil texture"]
    },
    {
        "id": "EC-R17",
        "name": "Occupational Health & Safety (OHS) Protocol",
        "category": "Minor",
        "weight": 1,
        "description": "Worker workplace safety provisions, ergonomic controls, personal protective equipment (PPE), and periodic health checks.",
        "keywords": ["occupational health", "ohs", "worker safety", "ppe", "medical examination", "ergonomics", "health surveillance"]
    },
    {
        "id": "EC-R18",
        "name": "Corporate Environment Responsibility (CER)",
        "category": "Minor",
        "weight": 1,
        "description": "Mandated CER/CSR infrastructure development commitments for local village communities per ministry guidelines.",
        "keywords": ["corporate environment responsibility", "cer", "csr", "local community", "community development", "drinking water scheme"]
    }
]

def get_all_rules() -> List[Dict[str, Any]]:
    """Returns the full list of 18 statutory EC rules."""
    return EC_RULES

def get_rule_by_id(rule_id: str) -> Dict[str, Any]:
    """Finds a rule definition by its unique identifier."""
    for rule in EC_RULES:
        if rule["id"] == rule_id:
            return rule
    raise KeyError(f"Rule ID '{rule_id}' not found in EC rules catalog.")
