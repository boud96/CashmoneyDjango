from core.base.models import Keyword


# TODO: Bet it could be done with better Django ORM, especially without query loops
def get_matching_keyword_objs(categorization_string: str):
    matching_keywords = Keyword.objects.none()
    if categorization_string is not None:
        for keyword in Keyword.objects.all():
            if keyword.value.lower().replace(" ", "") in categorization_string.lower().replace(" ", ""):
                matching_keywords = matching_keywords | Keyword.objects.filter(id=keyword.id)

        return matching_keywords
