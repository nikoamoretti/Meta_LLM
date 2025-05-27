def z_score(value, mean, stddev, higher_is_better=True):
    if stddev == 0:
        return 0.0
    if higher_is_better:
        return (value - mean) / stddev
    else:
        return -(value - mean) / stddev

# TODO: Add percentile and other normalization functions 