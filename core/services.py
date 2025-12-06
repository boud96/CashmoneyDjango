from dataclasses import dataclass
from typing import Optional, Dict, Any
from core.base.models import Keyword, BankAccount, CSVMapping


@dataclass
class CategorizationResult:
    subcategory: Optional[object] = None
    want_need_investment: Optional[str] = None
    ignore: bool = False
    is_category_overlap: bool = False
    is_uncategorized: bool = False

    def to_dict(self):
        return {
            "subcategory": self.subcategory,
            "want_need_investment": self.want_need_investment,
            "ignore": self.ignore,
        }


class CategorizationService:
    def __init__(self):
        self.keywords = list(Keyword.objects.all().order_by("description"))

        self.optimized_keywords = []
        for k in self.keywords:
            rules = k.rules if isinstance(k.rules, dict) else {}
            include = rules.get("include", [])
            exclude = rules.get("exclude", [])

            self.optimized_keywords.append(
                {
                    "obj": k,
                    "norm_include": [r.lower().replace(" ", "") for r in include if r],
                    "norm_exclude": [r.lower().replace(" ", "") for r in exclude if r],
                }
            )

        self.own_account_numbers = set(
            BankAccount.objects.values_list("account_number", flat=True)
        )

    def get_categorization_string(
        self, transaction_data: Dict[str, Any], csv_map: CSVMapping
    ) -> str:
        parts = []
        fields = csv_map.categorization_fields
        if isinstance(fields, str):
            import ast

            try:
                fields = ast.literal_eval(fields)
            except:  # noqa: E722
                fields = []

        for field_name in fields:
            val = transaction_data.get(field_name)
            if val is not None and val != "":
                parts.append(str(val))
        return " | ".join(parts)

    def apply_categorization(
        self, cat_string: str, transaction_data: Dict[str, Any] = None
    ) -> CategorizationResult:
        result = CategorizationResult()

        # --- A. Check for Self-Transfer ---
        if transaction_data:
            cp_account = transaction_data.get("counterparty_account_number")
            if cp_account:
                cp_account = str(cp_account).strip().replace(" ", "")
                clean_own = {str(x).replace(" ", "") for x in self.own_account_numbers}
                if cp_account in clean_own:
                    result.ignore = True
                    return result

        # --- B. Keyword Matching ---
        cat_string_clean = cat_string.lower().replace(" ", "")
        matched = []

        for item in self.optimized_keywords:
            keyword = item["obj"]
            norm_include = item["norm_include"]
            norm_exclude = item["norm_exclude"]

            if not norm_include:
                continue

            # Check Include
            include_match = all(r in cat_string_clean for r in norm_include)

            if include_match:
                # Check Exclude
                exclude_match = any(r in cat_string_clean for r in norm_exclude)

                if not exclude_match:
                    matched.append(keyword)

        # --- C. Result Determination ---
        if not matched:
            result.is_uncategorized = True
            return result

        if len(matched) == 1:
            k = matched[0]
            result.subcategory = k.subcategory
            result.want_need_investment = k.want_need_investment
            result.ignore = k.ignore
            return result

        # Handle Overlap
        first = matched[0]
        all_same = all(
            m.subcategory == first.subcategory
            and m.want_need_investment == first.want_need_investment
            and m.ignore == first.ignore
            for m in matched
        )

        if all_same:
            result.subcategory = first.subcategory
            result.want_need_investment = first.want_need_investment
            result.ignore = first.ignore
        else:
            result.is_category_overlap = True

        return result
