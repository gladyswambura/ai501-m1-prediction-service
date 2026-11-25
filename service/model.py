import math

def score(features):
    z = sum(features) / len(features)
    # Sigmoid: turns any number into a value from 0 to 1
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    return math.exp(z) / (1 + math.exp(z))