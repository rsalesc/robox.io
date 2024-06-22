# type: ignore
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class alias(auto):
    def __init__(self, *aliases):
        if len(aliases) == 0:
            raise ValueError('Cannot have empty alias() call.')
        for a in aliases:
            if not isinstance(a, str):
                raise ValueError(
                    f'All aliases for must be strings; found alias of type {type(a)} having value: {a}'
                )
        self.names = aliases
        self.enum_name = None

    def __repr__(self) -> str:
        return str(self)

    def __str__(self):
        if self.enum_name is not None:
            return self.enum_name
        return self.alias_repr

    @property
    def alias_repr(self) -> str:
        return str(f'alias:{list(self.names)}')

    def __setattr__(self, attr_name: str, attr_value: Any):
        if attr_name == 'value':
            ## because alias subclasses auto and does not set value, enum.py:143 will try to set value
            self.enum_name = attr_value
        else:
            super(alias, self).__setattr__(attr_name, attr_value)

    def __getattribute__(self, attr_name: str):
        """
        Refer these lines in Python 3.10.9 enum.py:

        class _EnumDict(dict):
            ...
            def __setitem__(self, key, value):
                ...
                elif not _is_descriptor(value):
                    ...
                    if isinstance(value, auto):
                        if value.value == _auto_null:
                            value.value = self._generate_next_value(
                                    key,
                                    1,
                                    len(self._member_names),
                                    self._last_values[:],
                                    )
                            self._auto_called = True
                        value = value.value
                    ...
                ...
            ...

        """
        if attr_name == 'value':
            if object.__getattribute__(self, 'enum_name') is None:
                ## Gets _auto_null as alias inherits auto class but does not set `value` class member; refer enum.py:142
                try:
                    return object.__getattribute__(self, 'value')
                except Exception:
                    from enum import _auto_null

                    return _auto_null
            return self
        return object.__getattribute__(self, attr_name)


_DEFAULT_REMOVAL_TABLE = str.maketrans(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    'abcdefghijklmnopqrstuvwxyz',
    ' -_.:;,',  ## Will be removed
)


class AutoEnum(str, Enum):
    """
    Utility class which can be subclassed to create enums using auto() and alias().
    Also provides utility methods for common enum operations.
    """

    def __init__(self, value: Union[str, alias]):
        self.aliases: Tuple[str, ...] = tuple()
        if isinstance(value, alias):
            self.aliases: Tuple[str, ...] = value.names

    @classmethod
    def _missing_(cls, enum_value: Any):
        ## Ref: https://stackoverflow.com/a/60174274/4900327
        ## This is needed to allow Pydantic to perform case-insensitive conversion to AutoEnum.
        return cls.from_str(enum_value=enum_value, raise_error=True)

    def _generate_next_value_(name, start, count, last_values):
        return name

    @property
    def str(self) -> str:
        return self.__str__()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.__class__.__name__ + '.' + self.name)

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def matches(self, enum_value: str) -> bool:
        return self is self.from_str(enum_value, raise_error=False)

    @classmethod
    def matches_any(cls, enum_value: str) -> bool:
        return cls.from_str(enum_value, raise_error=False) is not None

    @classmethod
    def does_not_match_any(cls, enum_value: str) -> bool:
        return not cls.matches_any(enum_value)

    @classmethod
    def display_names(cls, **kwargd) -> str:
        return str([enum_value.display_name(**kwargd) for enum_value in list(cls)])

    def display_name(self, *, sep: str = ' ') -> str:
        return sep.join(
            [
                (
                    word.lower()
                    if word.lower() in ('of', 'in', 'the')
                    else word.capitalize()
                )
                for word in str(self).split('_')
            ]
        )

    @classmethod
    def _initialize_lookup(cls):
        if (
            '_value2member_map_normalized_' not in cls.__dict__
        ):  ## Caching values for fast retrieval.
            cls._value2member_map_normalized_ = {}

            def _set_normalized(e, normalized_e_name):
                if normalized_e_name in cls._value2member_map_normalized_:
                    print('DEU MERDA')
                    raise ValueError(
                        f'Cannot register enum "{e.name}"; '
                        f'another enum with the same normalized name "{normalized_e_name}" already exists.'
                    )
                cls._value2member_map_normalized_[normalized_e_name] = e

            for e in list(cls):
                _set_normalized(e, cls._normalize(e.name))
                if len(e.aliases) > 0:
                    ## Add the alias-repr to the lookup:
                    _set_normalized(e, cls._normalize(alias(*e.aliases).alias_repr))
                    candidate_aliases = set(
                        cls._normalize(e_alias) for e_alias in e.aliases
                    )
                    if cls._normalize(e.name) in candidate_aliases:
                        candidate_aliases.remove(cls._normalize(e.name))
                    for e_alias in candidate_aliases:
                        _set_normalized(e, e_alias)

    @classmethod
    def from_str(cls, enum_value: str, raise_error: bool = True) -> Optional:
        """
        Performs a case-insensitive lookup of the enum value string among the members of the current AutoEnum subclass.
        :param enum_value: enum value string
        :param raise_error: whether to raise an error if the string is not found in the enum
        :return: an enum value which matches the string
        :raises: ValueError if raise_error is True and no enum value matches the string
        """
        if isinstance(enum_value, cls):
            return enum_value
        if enum_value is None and raise_error is False:
            return None
        if not isinstance(enum_value, str) and raise_error is True:
            raise ValueError(f'Input should be a string; found type {type(enum_value)}')
        cls._initialize_lookup()
        enum_obj: Optional[AutoEnum] = cls._value2member_map_normalized_.get(
            cls._normalize(enum_value)
        )
        if enum_obj is None and raise_error is True:
            raise ValueError(
                f'Could not find enum with value {repr(enum_value)}; available values are: {list(cls)}.'
            )
        return enum_obj

    @classmethod
    def _normalize(cls, x: str) -> str:
        ## Found to be faster than .translate() and re.sub() on Python 3.10.6
        return str(x).translate(_DEFAULT_REMOVAL_TABLE)

    @classmethod
    def convert_keys(cls, d: Dict) -> Dict:
        """
        Converts string dict keys to the matching members of the current AutoEnum subclass.
        Leaves non-string keys untouched.
        :param d: dict to transform
        :return: dict with matching string keys transformed to enum values
        """
        out_dict = {}
        for k, v in d.items():
            if isinstance(k, str) and cls.from_str(k, raise_error=False) is not None:
                out_dict[cls.from_str(k, raise_error=False)] = v
            else:
                out_dict[k] = v
        return out_dict

    @classmethod
    def convert_keys_to_str(cls, d: Dict) -> Dict:
        """
        Converts dict keys of the current AutoEnum subclass to the matching string key.
        Leaves other keys untouched.
        :param d: dict to transform
        :return: dict with matching keys of the current AutoEnum transformed to strings.
        """
        out_dict = {}
        for k, v in d.items():
            if isinstance(k, cls):
                out_dict[str(k)] = v
            else:
                out_dict[k] = v
        return out_dict

    @classmethod
    def convert_values(
        cls, d: Union[Dict, Set, List, Tuple], raise_error: bool = False
    ) -> Union[Dict, Set, List, Tuple]:
        """
        Converts string values to the matching members of the current AutoEnum subclass.
        Leaves non-string values untouched.
        :param d: dict, set, list or tuple to transform.
        :param raise_error: raise an error if unsupported type.
        :return: data structure with matching string values transformed to enum values.
        """
        if isinstance(d, dict):
            return cls.convert_dict_values(d)
        if isinstance(d, list):
            return cls.convert_list(d)
        if isinstance(d, tuple):
            return tuple(cls.convert_list(d))
        if isinstance(d, set):
            return cls.convert_set(d)
        if raise_error:
            raise ValueError(f'Unrecognized data structure of type {type(d)}')
        return d

    @classmethod
    def convert_dict_values(cls, d: Dict) -> Dict:
        """
        Converts string dict values to the matching members of the current AutoEnum subclass.
        Leaves non-string values untouched.
        :param d: dict to transform
        :return: dict with matching string values transformed to enum values
        """
        out_dict = {}
        for k, v in d.items():
            if isinstance(v, str) and cls.from_str(v, raise_error=False) is not None:
                out_dict[k] = cls.from_str(v, raise_error=False)
            else:
                out_dict[k] = v
        return out_dict

    @classmethod
    def convert_list(cls, ls: Union[List, Tuple]) -> List:
        """
        Converts string list itmes to the matching members of the current AutoEnum subclass.
        Leaves non-string items untouched.
        :param l: list to transform
        :return: list with matching string items transformed to enum values
        """
        out_list = []
        for item in ls:
            if isinstance(item, str) and cls.matches_any(item):
                out_list.append(cls.from_str(item))
            else:
                out_list.append(item)
        return out_list

    @classmethod
    def convert_set(cls, s: Set) -> Set:
        """
        Converts string list itmes to the matching members of the current AutoEnum subclass.
        Leaves non-string items untouched.
        :param s: set to transform
        :return: set with matching string items transformed to enum values
        """
        out_set = set()
        for item in s:
            if isinstance(item, str) and cls.matches_any(item):
                out_set.add(cls.from_str(item))
            else:
                out_set.add(item)
        return out_set

    @classmethod
    def convert_values_to_str(cls, d: Dict) -> Dict:
        """
        Converts dict values of the current AutoEnum subclass to the matching string value.
        Leaves other values untouched.
        :param d: dict to transform
        :return: dict with matching values of the current AutoEnum transformed to strings.
        """
        out_dict = {}
        for k, v in d.items():
            if isinstance(v, cls):
                out_dict[k] = str(v)
            else:
                out_dict[k] = v
        return out_dict


class TestEnum(AutoEnum):
    ACCEPTED = alias('accepted', 'ac')
    WRONG_ANSWER = alias('wrong answer', 'wa')


if __name__ == '__main__':
    print(TestEnum('ac'))
