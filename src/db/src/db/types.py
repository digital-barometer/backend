from sqlalchemy import Enum


def pg_enum(enum_class):
    return Enum(enum_class, values_callable=lambda values: [item.value for item in values])
