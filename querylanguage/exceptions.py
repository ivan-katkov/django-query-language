class FieldDoesNotExist(Exception):
    def __init__(self, field, message=None):
        self.field = field
        if message is None:
            super().__init__("Field '%s' does not exist" % field)
        super().__init__(message)

class InvalidQuery(Exception):
    def __init__(self):
        super().__init__("Invalid query")

class InvalidLiteral(Exception):
    def __init__(self):
        super().__init__("Invalid Literal")

class InvalidConeNumberArguments(Exception):
    def __init__(self):
        super().__init__("Cone statement should contains only 3 arguments: cone(ra, dec, radius)")