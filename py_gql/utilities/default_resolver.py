# -*- coding: utf-8 -*-
""" Default resolver behaviour """


def default_resolver(parent_value, args, context, info):
    """ Default resolver.

    :type parent_value: any
    :param parant_value: Value of the resolved parent node

    :type args: dict
    :param args: Coerced arguments

    :type context: any
    :param context: User provided context value

    :type info: ResolveInfo
    :param info: Resolution context

    :rype: any
    :returns: Resolved value

    Lookup order:

        1. non callable key in the parent_value (dict subclass only)
        2. result of callable(parent_value, args, context, info) key in the
           parent_value (dict subclass only)
        3. non callable attribute in the parent_value
        4. result of callable(args, context, info) attribute in the parent_value
        5. None
    """
    field_name = info.field_def.name
    if isinstance(parent_value, dict):
        field_value = parent_value.get(field_name, None)
        if callable(field_value):
            return field_value(parent_value, args, context, info)
        return field_value

    attr_value = getattr(parent_value, field_name, None)
    if callable(attr_value):
        return attr_value(args, context, info)
    return attr_value
