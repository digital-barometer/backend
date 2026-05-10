from dataclasses import dataclass

from db.models import Source


@dataclass(frozen=True, slots=True)
class SourceSearchQuery:
    source: Source
    query: str


@dataclass(frozen=True, slots=True)
class SearchPlan:
    query: str
    keywords: list[str]
    source_queries: list[SourceSearchQuery]


class QueryBuilder:
    def build(self, query: str, keywords: list[str], sources: list[Source]) -> SearchPlan:
        coverage = normalize_keywords(query, keywords)
        return SearchPlan(
            query=query,
            keywords=coverage,
            source_queries=[
                SourceSearchQuery(
                    source=source,
                    query=build_source_query(source, query, coverage),
                )
                for source in sources
            ],
        )


def normalize_keywords(query: str, keywords: list[str]) -> list[str]:
    values = [
        item.strip()
        for item in [query, *keywords]
        if item and item.strip()
    ]
    return list(dict.fromkeys(values))


def build_source_query(source: Source, query: str, keywords: list[str]) -> str:
    connector = source.config.get("connector")
    if connector == "pytrends_modern":
        return query

    terms = normalize_keywords(query, keywords)
    if len(terms) <= 1:
        return query

    if connector == "gdelt_doc":
        return _build_gdelt_query(query, terms)

    return " OR ".join(terms)


def _build_gdelt_query(query: str, terms: list[str]) -> str:
    valid_terms = [term for term in terms if is_valid_gdelt_keyword(term)]
    if not valid_terms:
        return query
    if len(valid_terms) == 1:
        return valid_terms[0]
    joined_terms = " OR ".join(
        f'"{term}"' if " " in term else term
        for term in valid_terms
    )
    return f"({joined_terms})"


def is_valid_gdelt_keyword(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 3 or len(stripped) > 60:
        return False
    return all(char.isalnum() or char.isspace() or char in {"-", "_"} for char in stripped)
