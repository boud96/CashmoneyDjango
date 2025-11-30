class URLConstants:
    ADMIN = "admin/"
    IMPORT_TRANSACTIONS = "import-transactions/"
    RECATEGORIZE_TRANSACTIONS = "recategorize-transactions/"
    CREATE_KEYWORDS = "create-keyword/"
    DELETE_KEYWORDS = "delete-keywords/"
    CREATE_CATEGORY = "create-category/"
    CREATE_SUBCATEGORY = "create-subcategory/"
    DELETE_CATEGORIES = "delete-categories/"
    DELETE_SUBCATEGORIES = "delete-subcategories/"
    CREATE_BANK_ACCOUNT = "create-bank-account/"
    DELETE_BANK_ACCOUNTS = "delete-bank-accounts/"
    CREATE_CSV_MAPPING = "create-csv-mapping/"
    DELETE_CSV_MAPPINGS = "delete-csv-mappings/"


class ModelConstants:
    WNI_CHOICES = [
        ("want", "Want"),
        ("investment", "Investment"),
        ("need", "Need"),
        ("other", "Other"),
    ]
    INCLUDE_RULE_KEY = "include"
    EXCLUDE_RULE_KEY = "exclude"


class WidgetConstants:
    WNI_COLORS = {
        "Need": "#54a0ff",  # Blue
        "Want": "#ff9f43",  # Orange
        "Investment": "#1dd1a1",  # Green
        "None": "#c8d6e5",  # Grey
        "Uncategorized": "#c8d6e5",
    }
