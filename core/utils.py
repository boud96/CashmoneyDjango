from django.db.models import Q

from core.base.models import Keyword


def get_matching_keyword_objs(categorization_strings: list):
    matching_keywords = Keyword.objects.none()

    for string in categorization_strings:
        if string is not None:
            query = Q()
            for keyword in Keyword.objects.all():
                if keyword.value in string:
                    query |= Q(pk=keyword.pk)
            matching_keywords = matching_keywords | Keyword.objects.filter(query)

    return matching_keywords.distinct()