from service.validation import validate
from service.model import score

for request in [{"features": [1, 2, 3]}, {"features": "hello"}]:
    try:
        print("score:", score(validate(request)))
    except ValueError as error:
        print("rejected:", error)