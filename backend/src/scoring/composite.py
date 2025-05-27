def category_composite(z_scores):
    # z_scores: list of floats for a category
    if not z_scores:
        return 0.0
    return sum(z_scores) / len(z_scores)

def overall_composite(category_zs):
    # category_zs: list of category composite scores
    if not category_zs:
        return 0.0
    return sum(category_zs) / len(category_zs)

# TODO: Add refresh() to update materialized views 