from sqlglot import parse_one, exp

from django.core import exceptions as django_exceptions
from . import exceptions
from django.db.models import Value, Q, F
from django.db.models.lookups import (Exact, IContains, GreaterThan, LessThan,
    GreaterThanOrEqual, LessThanOrEqual, In, IsNull)
from django.db.models.fields import json

class Parser:

    def __init__(self, model, database='postgres', date_format='%Y-%m-%d'):
        self.query = None
        self.model = model
        self.date_format = date_format
        self.database = database
        # extraparams to keep information on Cone-queries and required aliases
        self.extra_params = dict(cones=[], aliases=dict())

    def parse(self, query):
        """
        Parse SQL-like WHERE clause and return Django Q objects which can be 
        used in Model.objects.filter()
        """

        self.query = query
        parsed = parse_one(query, read=self.database)
        return self._resolve(parsed)

    def _resolve(self, p):
        """Resolve SQLglot expression tree to Q objects and F aliases"""

        # lets go from simple to complex structures
        if isinstance(p, exp.Literal):
            if p.is_string:
                return Value(p.this)
            elif p.is_int:
                return Value(int(p.this))
            elif p.is_number:
                return Value(float(p.this))
            else:
                raise exceptions.InvalidLiteral()

        elif isinstance(p, exp.Column):
            if p.this.quoted:
                # This is the case of double quoted string parsed as column identifier in SQL.
                # It is not assumed to use double quotes in the column name.
                return Value(p.this.this)
            else:
                return self._resolve_column(p)

        elif isinstance(p, exp.Neg):
            if isinstance(p.this, exp.Literal) & (not p.this.is_string):
                # this is simplest way of somewhat number
                return Value(-self._resolve(p.this).value)
            else:
                # this can be more complicated expression
                return -self._resolve(p.this)

        elif isinstance(p, exp.Not):
            return ~Q(self._resolve(p.this))

        elif isinstance(p, exp.Paren):
            # return ExpressionWrapper(self._resolve(p.this), None)
            return self._resolve(p.this)

        # Logical operators
        elif isinstance(p, exp.And):
            return Q(self._resolve(p.left)) & Q(self._resolve(p.right))

        elif isinstance(p, exp.Or):
            return Q(self._resolve(p.left)) | Q(self._resolve(p.right))

        # Comparison operators
        elif isinstance(p, exp.EQ):
            if isinstance(p.right, exp.Null):
                return IsNull(self._resolve(p.left), True)
            else:
                return Exact(self._resolve(p.left), self._resolve(p.right))

        elif isinstance(p, exp.Is):
            if isinstance(p.right, exp.Null):
                return IsNull(self._resolve(p.left), True)
            else:
                return Exact(self._resolve(p.left), self._resolve(p.right))

        elif isinstance(p, exp.NEQ):
            if isinstance(p.right, exp.Null):
                return IsNull(self._resolve(p.left), False)
            else:
                return ~Exact(self._resolve(p.left), self._resolve(p.right))

        elif isinstance(p, exp.GT):
            return GreaterThan(self._resolve(p.left), self._resolve(p.right))

        elif isinstance(p, exp.LT):
            return LessThan(self._resolve(p.left), self._resolve(p.right))

        elif isinstance(p, exp.GTE):
            return GreaterThanOrEqual(self._resolve(p.left), self._resolve(p.right))

        elif isinstance(p, exp.LTE):
            return LessThanOrEqual(self._resolve(p.left), self._resolve(p.right))

        elif isinstance(p, exp.RegexpLike):
            return IContains(self._resolve(p.this), self._resolve(p.expression))

        # Math operators
        elif isinstance(p, exp.Add):
            return self._resolve(p.left) + self._resolve(p.right)

        elif isinstance(p, exp.Sub):
            return self._resolve(p.left) - self._resolve(p.right)

        elif isinstance(p, exp.Mul):
            return self._resolve(p.left) * self._resolve(p.right)

        elif isinstance(p, exp.Div):
            return self._resolve(p.left) / self._resolve(p.right)

        # Special operators
        elif isinstance(p, exp.Between):
            return GreaterThanOrEqual(self._resolve(p.this), self._resolve(p.args['low'])) & \
                   LessThanOrEqual(self._resolve(p.this), self._resolve(p.args['high']))

        elif isinstance(p, exp.In):
            return In(self._resolve(p.this), [self._resolve(r) for r in p.expressions])

        # Astronomy specific syntax we extensively used in out projects.
        # Function cone(ra, dec, radius)
        elif isinstance(p, exp.Anonymous) and p.this.lower() == 'cone':
            
            return self._resolve_cone(p)

        else:
            raise exceptions.InvalidQuery()

    def _resolve_column(self, p):
        """Resolve column.
        Related fields are possible but less than 3 nested levels.
        f1.f2.f3.f4 - should be still valid. But only two embedded levels have been tested.
        """
        model = self.model

        identifiers = [prt.this for prt in p.parts]

        def check_related_fields(model, identifiers):
            model_fields = [f.name for f in model._meta.fields]
            model_fields_related = [f.name for f in model._meta.fields if f.is_relation]
            
            # call custom exception to test which exactly field cause an error in the test suite
            try:
                field = model._meta.get_field(identifiers[0])
            except django_exceptions.FieldDoesNotExist:
                raise exceptions.FieldDoesNotExist(identifiers[0])
            
            if len(identifiers) == 1:
                if not identifiers[0] in model_fields:
                    raise exceptions.FieldDoesNotExist(identifiers[0])
            else:
                # nested column notation can be Related or JSONField only. Otherwise, raise an error
                if field.is_relation:
                    check_related_fields(field.related_model, identifiers[1:])
                elif not isinstance(field, json.JSONField):
                    msg = f"{field.name} is not Relation field or JSON field"
                    raise exceptions.FieldDoesNotExist(field, message=msg)
                    
                
        check_related_fields(model, identifiers)    
        full_field_name = "__".join([part.this for part in p.parts])
        # print("----> full_field_name: ", full_field_name)
        
        return F(full_field_name)

        # while len(parts) > 1:
        #     # iterate over all nested levels
        #     current_identifier = parts.pop(0)
        #     field = model._meta.get_field(current_identifier)

        #     # print("debug1:", field)
        #     if isinstance(field, json.JSONField):
        #         # print("debug2:", field)
        #         break
        #     # print("debug3:", field)
        #     model = field.related_model

        # try:
        #     # check field name existence
        #     # model._meta.get_field(current_identifier)
            

        #     full_field_name = "__".join([part.this for part in p.parts])
        #     print("----> full_field_name: ", full_field_name)
            
        #     check_related_fields(model, identifiers)
            
        #     return F(full_field_name)
        # except django_exceptions.FieldDoesNotExist:
        #     raise exceptions.FieldDoesNotExist(full_field_name)

    def _resolve_cone(self, p):

        if len(p.expressions) != 3:
            raise exceptions.InvalidConeNumberArguments

        cone_params = dict(
            cone_ra = self._resolve(p.expressions[0]).value,
            cone_dec = self._resolve(p.expressions[1]).value,
            cone_radius = self._resolve(p.expressions[2]).value,
            )
        # Check whether this is the first Cone statement or 
        # there are already several in the query.
        cone_index = len(self.extra_params['cones'])
        cone_index_str = "" if cone_index == 0 else str(cone_index)

        # Extend dictionary with Cone parameters
        self.extra_params['cones'].append(cone_params)

        # Build and return corresponding Django Q object with boolean
        # statement cone_query=1 or cone_query1=1 etc
        kwargs = dict()
        kwargs[f"cone_query{cone_index_str}"] = True

        return Q(**kwargs)
