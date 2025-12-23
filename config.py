# config.py - AI Privacy Compliance Configuration (English Version)
# -*- coding: utf-8 -*-

# ===================== GDPR Privacy Baseline =====================
PRIVACY_BASELINE = [
    {"id": 1, "name": "Data Minimization (GDPR Art.5)", "desc": "Collect only necessary data; avoid indefinite storage.", "suggestion": "Remove irrelevant PII columns and define a clear retention period."},
    {"id": 2, "name": "Transparency & Consent (GDPR Art.6/17)", "desc": "User consent must be explicit and revocable.", "suggestion": "Add a clear Privacy Policy and Consent Form."},
    {"id": 3, "name": "Sensitive Data Protection (GDPR Art.9)", "desc": "Special categories of data require strict protection.", "suggestion": "Apply de-identification (masking) or Differential Privacy."},
    {"id": 4, "name": "Storage Security (AI Act Art.25)", "desc": "Data must be encrypted at rest and in transit.", "suggestion": "Implement AES-256 encryption or use secure storage solutions."},
    {"id": 5, "name": "Accountability & DPIA (AI Act Art.14)", "desc": "High-risk systems require a Data Protection Impact Assessment.", "suggestion": "Perform a DPIA and implement human oversight mechanisms."}
]

# ===================== AI Act Risk Decision Logic =====================
AI_ACT_DECISION_TREE = {
    # Forbidden (Unacceptable Risk)
    "forbidden_behavior": [
        "social scoring", "subliminal technique", "dark pattern", "manipulative",
        "biometric categorization", "emotion recognition", "real-time biometric"
    ],
    # High Risk
    "high_risk_app": [
        "biometric", "critical infrastructure", "education", "vocational training",
        "employment", "recruitment", "credit scoring", "loan", "law enforcement", "migration", "justice"
    ],
    # Profiling Keywords
    "profiling_keywords": ["profiling", "prediction", "behavior analysis", "tracking", "scoring", "automated decision"]
}

# ===================== Domain-Business Scenario Config =====================
DOMAIN_BUSINESS_CONFIG = {
    "education": {
        "grading_tool": {
            "core_function": "Student Grading & Feedback",
            "necessary_data": [
                {"name": "Student Name", "granularity": "Full Name"},
                {"name": "Student ID", "granularity": "Unique ID"},
                {"name": "Assignment ID", "granularity": "Unique ID"}
            ],
            "forbidden_data": ["Home Address", "Parent Income", "Social Media", "Birth Date", "Student Photo", "Religion"]
        },
        "tutoring_platform": {
            "core_function": "Online Tutoring",
            "necessary_data": [
                {"name": "Student Name", "granularity": "Full Name"},
                {"name": "Grade Level", "granularity": "Grade Only (e.g. Grade 3)"}
            ],
            "forbidden_data": ["Home Phone", "Family Income", "Home Address", "National ID"]
        },
        "default": {
            "core_function": "General Education Service",
            "necessary_data": [{"name": "Student Name", "granularity": "Full Name"}],
            "forbidden_data": ["Home Address", "Parent Income", "Social Media"]
        }
    },
    "medical": {
        "diagnosis_tool": {
            "core_function": "Clinical Diagnosis Assistance",
            "necessary_data": [
                {"name": "Medical Record ID", "granularity": "Unique ID"},
                {"name": "Diagnosis", "granularity": "Specific Condition"},
                {"name": "Symptoms", "granularity": "Key Symptoms"}
            ],
            "forbidden_data": ["Home Address", "Family Contact", "Occupation", "Unrelated History", "Patient Photo"]
        },
        "telehealth": {
            "core_function": "Remote Consultation",
            "necessary_data": [
                {"name": "Medical Record ID", "granularity": "Unique ID"},
                {"name": "Prescription", "granularity": "Medication Details"}
            ],
            "forbidden_data": ["National ID", "Income", "Unrelated Health Data"]
        },
        "default": {
            "core_function": "Medical Service",
            "necessary_data": [{"name": "Medical Record ID", "granularity": "Unique ID"}],
            "forbidden_data": ["Home Address", "Family Contact", "Unrelated History"]
        }
    },
    "finance": {
        "risk_control": {
            "core_function": "Fraud Detection",
            "necessary_data": [
                {"name": "Card Last 4 Digits", "granularity": "Masked"},
                {"name": "Phone Number", "granularity": "Masked"},
                {"name": "Transaction Amount", "granularity": "Exact Amount"}
            ],
            "forbidden_data": ["Full Card Number", "Full National ID", "Social Media", "Home Address", "Occupation"]
        },
        "credit_scoring": {
            "core_function": "Credit Assessment",
            "necessary_data": [
                {"name": "National ID Last 6 Digits", "granularity": "Masked"},
                {"name": "Credit Score", "granularity": "Score Value"}
            ],
            "forbidden_data": ["Full National ID", "Family Income", "Social Relations", "Race", "Religion"]
        },
        "default": {
            "core_function": "Financial Service",
            "necessary_data": [{"name": "Card Last 4 Digits", "granularity": "Masked"}],
            "forbidden_data": ["Full Card Number", "Full National ID", "Home Address"]
        }
    },
    "general": {
        "login_system": {
            "core_function": "User Authentication",
            "necessary_data": [{"name": "Phone Number", "granularity": "Masked"}],
            "forbidden_data": ["National ID", "Face Data", "Address", "Occupation"]
        },
        "data_collection": {
            "core_function": "Information Collection",
            "necessary_data": [{"name": "Name", "granularity": "Full Name"}, {"name": "Email", "granularity": "Full Email"}],
            "forbidden_data": ["National ID", "Address", "Social Media"]
        },
        "default": {
            "core_function": "General Service",
            "necessary_data": [{"name": "Email", "granularity": "Full Email"}],
            "forbidden_data": ["National ID", "Face Data", "Address"]
        }
    }
}

# ===================== Domain Specific Config =====================
DOMAIN_CONFIG = {
    "general": {
        "name": "General Domain",
        "encryption": ["Encryption", "AES", "TLS", "HTTPS"],
        "consent": ["Consent", "Agreement", "Authorize"],
        "sensitive_data": ["ID", "Phone", "Face", "Biometric"]
    },
    "education": {
        "name": "Education Domain",
        "encryption": ["AES-256", "Dual Encryption"],
        "consent": ["Guardian Consent", "Parental Consent", "Dual Authorization"],
        "sensitive_data": ["Child Data", "Student Data", "Minor", "Grade", "Exam"]
    },
    "medical": {
        "name": "Medical Domain",
        "encryption": ["AES-256", "End-to-End Encryption"],
        "consent": ["Explicit Consent", "Patient Authorization", "Written Consent"],
        "sensitive_data": ["Medical Record", "Patient Data", "Diagnosis", "Health Data", "Genetics"]
    },
    "finance": {
        "name": "Financial Domain",
        "encryption": ["Dual Encryption", "AES-256", "HSM"],
        "consent": ["Double Confirmation", "Two-Factor Authorization"],
        "sensitive_data": ["Credit Card", "Bank Account", "Credit Score", "Transaction", "Loan"]
    }
}

# ===================== NLP / Synonym Config =====================
SYNONYM_DICT = {
    "data_minimization": ["necessary data", "minimum collection", "storage limit", "retention period", "only necessary"],
    "consent": ["consent", "agreement", "permission", "authorization", "allow", "opt-in"],
    "sensitive_data": ["id card", "phone", "face", "child", "student", "medical", "patient", "bank", "credit", "biometric"],
    "encryption": ["encrypt", "aes", "sha", "protect", "secure", "tls", "ssl"],
    "dpia": ["dpia", "impact assessment", "privacy assessment", "human oversight", "manual review"],
    "business_scenario": ["grading", "tutoring", "diagnosis", "telehealth", "risk control", "credit scoring", "login"],
    "revoke": ["withdraw", "revoke", "cancel", "opt-out"],
    "cancel": ["withdraw", "revoke", "cancel"]
}

# Negative words for semantic analysis
NEGATIVE_WORDS = ["no", "not", "without", "lack", "fail", "never", "prohibit", "unable", "denied"]