class URLConstants:
    ADMIN = "admin/"
    IMPORT_TRANSACTIONS = "import-transactions/"
    RECATEGORIZE_TRANSACTIONS = "recategorize-transactions/"
    CREATE_KEYWORDS = "create-keywords/"
    DELETE_KEYWORDS = "delete-keywords/"

class ModelConstants:
    WNI_CHOICES = [
        ("want", "Want"),
        ("investment", "Investment"),
        ("need", "Need"),
        ("other", "Other"),
]
    INCLUDE_RULE_KEY = "include"
    EXCLUDE_RULE_KEY = "exclude"