from .core_funcs import DSL_FUNCTIONS as CORE_FUNCS
from .math_funcs import DSL_FUNCTIONS as MATH_FUNCS
from .string_funcs import DSL_FUNCTIONS as STRING_FUNCS
from .time_funcs import DSL_FUNCTIONS as TIME_FUNCS
from .collection_funcs import DSL_COLLECTION_FUNCS as COLLECTION_FUNCS

DSL_FUNCTIONS = {}
for group in [
    CORE_FUNCS,
    MATH_FUNCS,
    STRING_FUNCS,
    TIME_FUNCS,
    COLLECTION_FUNCS,
]:
    DSL_FUNCTIONS.update(group)

DSL_FUNCTION_REGISTRY = {k: v[0] for k, v in DSL_FUNCTIONS.items()}
DSL_FUNCTION_SIG = {k: v[1] for k, v in DSL_FUNCTIONS.items()}
