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


class ModelConstants:
    WNI_CHOICES = [
        ("want", "Want"),
        ("investment", "Investment"),
        ("need", "Need"),
        ("other", "Other"),
    ]
    INCLUDE_RULE_KEY = "include"
    EXCLUDE_RULE_KEY = "exclude"
