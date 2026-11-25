import math

def validate(request):
    if not isinstance(request, dict):
        raise ValueError("request must be a dictionary")
    features = request.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("features must be a non-empty list")
    for x in features:
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise ValueError("every feature must be a number")
        try:
            finite = math.isfinite(x)
        except OverflowError:  # integer too big to use
            finite = False
        if not finite:
            raise ValueError("numbers must be finite")
    return features