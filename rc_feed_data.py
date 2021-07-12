from dataclasses import dataclass, field
from typing import List


@dataclass
class Category():
    code: str
    id: str
    name: str


# Spa category is not supported currently due to complex API request/response
catalog_data = [
    Category('excursions', '1002', 'Shore Excursions'),
    Category('beverage', '1012', 'Beverage Packages'),
    Category('internet', '1051', 'Internet & More'),
    # Category('spa', '1021', 'Spa & Fitness'),
    Category('entertainment', '1031', 'Entertainment'),
    Category('activities', '1032', 'Activities')
]

DEFAULT_CATEGORY = Category('dining', '1011', 'Dining')
catalog_data.append(DEFAULT_CATEGORY)

category_list = [category.code for category in catalog_data]

def get_matching_category(query):
    return next((category_obj for category_obj in catalog_data if query == category_obj.code), DEFAULT_CATEGORY)


@dataclass
class QueryStatus():
    errors: List[str]
    ok: bool = True

    def refresh(self):
        self.ok = False if self.errors else True


@dataclass
class _BaseQuery():
    query: str
    status: QueryStatus
    category: str = None
    category_obj: Category = None

    def validate_query(self):
        if not self.query:
            self.query = DEFAULT_CATEGORY.code
        if not (self.query in category_list):
            self.status.errors.append(f"Invalid query, must be one of the following: " + ', '.join(category_list))
        self.category_obj = get_matching_category(self.query)
        self.category = self.category_obj.id


@dataclass
class RcSearchQuery(_BaseQuery):
    __slots__ = ['query', 'category']

    def __post_init__(self):
        if not isinstance(self.query, str):
            self.status.errors.append('Invalid query')

        self.validate_query()
        self.status.refresh()
