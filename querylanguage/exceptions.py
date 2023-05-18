class FieldDoesNotExist(Exception):
    def __init__(self, field):
        self.field = field
        super().__init__("Field '%s' does not exist" % field)

class InvalidQuery(Exception):
    def __init__(self):
        super().__init__("Invalid query")

class InvalidLiteral(Exception):
    def __init__(self):
        super().__init__("Invalid Literal")

class InvalidConeNumberArguments(Exception):
    def __init__(self):
        super().__init__("Cone statement should contains only 3 arguments: cone(ra, dec, radius)")