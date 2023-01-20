
# standard
import hashlib
import operator
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


def get_match_length(search_term: str, word: str) -> int:
    """
    Use sliding windows (masks) of reducing sizes on search_term
    to find the length of maximum matching span with input word.
    E.g. slaughter & manslaughter give a match length of 8.
    :param search_term: string 1
    :param word: string 2
    :return: Length of the biggest matching span.
    """
    for window_span in reversed(range(len(search_term) + 1)):
        for start in range(len(search_term) + 1 - window_span):
            if search_term[start : start+window_span] in word:
                return window_span
    return 0


def normalize_address_word(word: str) -> str:
    """
    Converts word to lowercase
    removes generic components ("street", "boulevard")
    removes spaces and dots from beginning and end.
    Meant to be used before comparing words.
    :param word: Word to normalize
    :return: Normalized word string
    """
    disposable_strings = ["tn", "pst", "tänav", "puiestee", "linn", "linnaosa", "st", "ave", "blvd"]
    word_normalized = word.strip(". ")
    for string in disposable_strings:
        word_normalized = re.sub(rf"\s{string}$", "", word_normalized).strip(". ")
    return word_normalized


def get_similarity_score(search_term: str, word: str) -> float:
    """
    Returns a similarity score based on the proportion of maximum matching span
    to the length of search term and word that is being matched.
    :param search_term: Search term string.
    :param word: String that is being matched
    :return: The match score: a number between 0 and 1
    """
    match_length = get_match_length(search_term.lower(), word.lower())
    match_score = 0.5 * (match_length / len(search_term)) + 0.5 * (match_length / len(word))
    return match_score


def parse_condition(condition: str) -> dict:
    """
    Parses comparison operation from string (<, <=, >, >=, ==, !=).
    :param condition: A comparison operation string (e.g. "price_eur <= 300000")
    :return: A dict with keys "operation": comparison operator,
    "variable": left-hand side value in input and
    "value": right-hand side value in input.
    """
    operators = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne}

    pattern = re.compile(r"(?P<variable>^\w+)\s*(?P<operator>[<>!=]+)(?P<value>.+$)")
    condition_components = pattern.match(condition.strip())

    comparison_operation = operators[condition_components["operator"].strip()]
    variable = condition_components["variable"].strip(" .'\"")
    value = condition_components["value"].strip()
    return {"operation": comparison_operation, "variable": variable, "value": value}


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

    def typecast_value(self, variable, value):
        if value is None:
            correct_type_value = type(self.__class__.__dict__[variable])()
        else:
            correct_type_value = type(self.__class__.__dict__[variable])(value)
        return correct_type_value

    def __setattr__(self, variable, value):
        """
        Check if variable is allowed and typecast it to the correct type.
        If value is None, enter empty value of the appropriate type.
        """
        if variable in self.__class__.__dict__:
            correct_type_value = self.typecast_value(variable, value)
            super().__setattr__(variable, correct_type_value)
        else:
            raise UserWarning(f"'{variable}' is not a variable of class {type(self).__name__}. Value not inserted!")

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

    def fits_conditions(self, *args) -> list[bool]:
        """
        Takes statements in the form "n_rooms < 3", "city == 'Põhja-Tallinna linnaosa'" etc.
        Evaluates each and returns a list of booleans.
        :param args: Statements about listing variables
        :return: Booleans for each input statement
        """
        conditions = [parse_condition(condition) for condition in args]
        results = list()
        for condition in conditions:
            comparison_operation = condition["operation"]
            listing_value = self.__getattribute__(condition["variable"])
            listing_value = listing_value.strip(" .'\"") if isinstance(listing_value, str) else listing_value
            comparison_value = self.typecast_value(condition["variable"], condition["value"].strip(" .'\""))
            results += [comparison_operation(listing_value, comparison_value)]
        return results

    def matches_address(self, **kwargs) -> bool:
        """
        Checks if listing address matches input address.
        :param kwargs: Takes parameters city (str), street(str) and house_number(int, str or list[(int, str)]).
        :return: Returns True if input parameters match closely enough to the listing address.
        """
        similarity_threshold = 0.88
        city_search_term = kwargs.get("city", "")
        street_search_term = kwargs.get("street", "")
        house_number_search_terms = kwargs.get("house_number", [])
        # Make sure house number search terms are a list of str elements
        house_number_search_terms = house_number_search_terms if isinstance(house_number_search_terms, list) \
            else [house_number_search_terms]
        house_number_search_terms = [str(element) for element in house_number_search_terms]

        city_search_term = normalize_address_word(city_search_term)
        street_search_term = normalize_address_word(street_search_term)
        city = normalize_address_word(self.city)
        street = normalize_address_word(self.street)

        if city_search_term and get_similarity_score(city_search_term, city) < similarity_threshold:
            return False
        if get_similarity_score(street_search_term, street) < similarity_threshold:
            return False
        if self.house_number not in house_number_search_terms:
            return False
        return True
