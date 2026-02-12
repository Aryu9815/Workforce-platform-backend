from pydantic import EmailStr

class NormalizedEmailStr(EmailStr):
    @classmethod
    def __get_validators__(cls):
        yield cls.normalize
        yield from super().__get_validators__()

    @classmethod
    def normalize(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
        return value
