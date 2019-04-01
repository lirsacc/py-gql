@schema.resolver("Query.hero")
def resolve_hero(_root, ctx, _info):
    return ctx["db"][2000]  # R2-D2


@schema.resolver("Query.characters")
def resolve_characters(_root, ctx, _info):
    return ctx["db"].items()


@schema.resolver("Query.character")
def resolve_character(_root, ctx, _info, *, id):
    return ctx["db"].get(id, None)
