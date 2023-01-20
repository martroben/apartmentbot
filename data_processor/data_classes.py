
import hashlib
import re


def get_class_variables(class_object: (object, str)) -> dict:
    """
    Helper function to get class variables (without dunder variables and functions.)
    :param class_object: Class object or object name string
    :return: dict with names and values of class variables
    """
    if isinstance(class_object, str):
        class_object = eval(class_object)
    return {key: value for key, value in class_object.__dict__.items()
            if not key.startswith("__") and not callable(value)}


class Listing:

    id = str()
    portal = str()
    active = int()
    reported = int()
    url = str()
    image_url = str()
    address = str()
    city = str()
    street = str()
    house_number = str()
    apartment_number = str()
    n_rooms = int()
    area_m2 = float()
    price_eur = float()
    construction_year = int()
    date_listed = float()
    date_scraped = float()
    date_unlisted = float()

    # Variables to be used for comparing whether listings are equal.
    __eq_variables__ = ["id", "portal", "address", "area_m2", "price_eur"]

    def __setattr__(self, key, value):
        """
        Check if variable is allowed and typecast it to the correct type.
        If value is None, enter empty value of the appropriate type.
        """
        if key in self.__class__.__dict__:
            if value is None:
                value = type(self.__class__.__dict__[key])()
            else:
                value = type(self.__class__.__dict__[key])(value)
            super().__setattr__(key, value)
        else:
            raise UserWarning(f"'{key}' is not a variable of class {type(self).__name__}. Value not inserted!")

    def __init__(self):
        # Copy class variable default values to instance variables (so that vars() would work).
        class_variables = get_class_variables(self.__class__)
        for key, value in class_variables.items():
            setattr(self, key, value)

    def make_from_dict(self, listing_dict: dict):
        """Set values of variables from a dict"""
        for key, value in listing_dict.items():
            setattr(self, key, value)
        return self

    def __str__(self):
        return f"{self.id} | {self.address} | {self.price_eur} eur"

    def __eq__(self, other):
        """
        If  compared to another Listing object, return true only if all variables in the dunder variable
        __eq_variables__ match.
        """
        if isinstance(other, Listing):
            return all([self.__getattribute__(element) == other.__getattribute__(element)
                        for element in self.__eq_variables__])
        return NotImplemented

    def __hash__(self):
        """
        Hashing function to use listings in a set (i.e. detect unique listings).
        """
        # If id is self-generated (i.e. starts with X), don't use id in hashing.
        if re.match("^X", self.id):
            return hash((self.portal, self.address, self.area_m2, self.price_eur))
        else:
            return hash((self.id, self.portal, self.address, self.area_m2, self.price_eur))

    def assign_random_id(self):
        """
        Generates (hopefully unique) id based on listing address and area_m2.
        :return: 7-character ID starting with X
        """
        hash_length = 7
        hash_seed = f"{str(self.area_m2)} {self.address}"
        listing_hash = hashlib.shake_128(hash_seed.encode()).hexdigest(int(hash_length - 1 / 2))
        listing_id = f"X{listing_hash}".upper()
        self.id = listing_id

    def fits_criteria(*args) -> list[bool]:
        """
        Takes statements in the form "n_rooms < 3", "city == 'Põhja-Tallinna linnaosa'" etc.
        Evaluates each and returns a list of booleans.
        :param args: Statements about listing variables
        :return: Booleans for each input statement
        """
        return [eval(f"self.{condition}") for condition in args]
