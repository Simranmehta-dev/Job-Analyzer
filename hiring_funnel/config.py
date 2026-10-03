"""Constants that define the synthetic hiring world.

The numbers here deliberately plant a few real-world patterns in the data
(a high-volume but weak source, a bottleneck stage, a slow recruiter) so the
analytics layer has something genuine to discover. Tests assert that it does.
"""

STAGES = [
    "Applied",
    "Recruiter Screen",
    "Technical Assessment",
    "Interview",
    "Final Round",
    "Offer",
    "Hired",
]

# source -> (share of applications, multiplier on early-stage advance odds)
SOURCES = {
    "Job Board": (0.38, 0.60),
    "LinkedIn": (0.27, 0.95),
    "Company Website": (0.15, 0.90),
    "Campus": (0.12, 1.10),
    "Referral": (0.08, 1.60),
}

# (department, job title, share of applications, multiplier on assessment duration)
ROLES = [
    ("Engineering", "Software Engineer", 0.30, 1.3),
    ("Data & Analytics", "Data Analyst", 0.25, 1.1),
    ("Data & Analytics", "Data Scientist", 0.10, 1.2),
    ("Finance", "Financial Analyst", 0.20, 0.9),
    ("Operations", "Operations Associate", 0.15, 0.8),
]

# recruiter -> multiplier on days spent in the first two stages
RECRUITERS = {
    "Ananya Rao": 1.0,
    "Dev Malhotra": 1.8,
    "Priya Nair": 0.9,
    "Karan Shah": 1.0,
    "Meera Iyer": 1.1,
}

# probability of advancing out of stage N (keyed by stage_order, 1-based)
BASE_ADVANCE = {1: 0.50, 2: 0.60, 3: 0.36, 4: 0.60, 5: 0.60, 6: 0.85}

# mean days spent in stage N before a decision (keyed by stage_order)
MEAN_DAYS = {1: 3.0, 2: 4.0, 3: 9.0, 4: 6.0, 5: 5.0, 6: 4.0}

# stages whose advance odds depend on candidate source quality
SOURCE_SENSITIVE_STAGES = (1, 2, 3)
MAX_ADVANCE = 0.90
