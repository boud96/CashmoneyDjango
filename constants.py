class URLConstants:
    ADMIN = "admin/"
    IMPORT_TRANSACTIONS = "import-transactions/"
    RECATEGORIZE_TRANSACTIONS = "recategorize-transactions/"
    CREATE_KEYWORDS = "create-keywords/"
    DELETE_KEYWORDS = "delete-keywords/"
    CREATE_CATEGORY = "create-categories/"
    CREATE_SUBCATEGORY = "create-subcategories/"
    DELETE_CATEGORIES = "delete-categories/"
    DELETE_SUBCATEGORIES = "delete-subcategories/"


class ModelConstants:
    WNI_CHOICES = [
        ("want", "Want"),
        ("investment", "Investment"),
        ("need", "Need"),
        ("other", "Other"),
    ]
    INCLUDE_RULE_KEY = "include"
    EXCLUDE_RULE_KEY = "exclude"
