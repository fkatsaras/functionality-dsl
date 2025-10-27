from .core_funcs import DSL_FUNCTIONS as CORE_FUNCS
from .math_funcs import DSL_FUNCTIONS as MATH_FUNCS
from .string_funcs import DSL_FUNCTIONS as STRING_FUNCS
from .time_funcs import DSL_FUNCTIONS as TIME_FUNCS
from .collection_funcs import DSL_COLLECTION_FUNCS as COLLECTION_FUNCS
from .validation_funcs import DSL_VALIDATION_FUNCS as VALIDATION_FUNCS
from .validators import DSL_VALIDATORS, VALIDATOR_FUNCTIONS, VALIDATOR_SIGNATURES

DSL_FUNCTIONS = {}
for group in [
    CORE_FUNCS,
    MATH_FUNCS,
    STRING_FUNCS,
    TIME_FUNCS,
    COLLECTION_FUNCS,
    VALIDATION_FUNCS,
    DSL_VALIDATORS,
]:
    DSL_FUNCTIONS.update(group)

DSL_FUNCTION_REGISTRY = {k: v[0] for k, v in DSL_FUNCTIONS.items()}
DSL_FUNCTION_SIG = {k: v[1] for k, v in DSL_FUNCTIONS.items()}

# Export validators separately for validation-specific use
__all__ = [
    'DSL_FUNCTIONS',
    'DSL_FUNCTION_REGISTRY',
    'DSL_FUNCTION_SIG',
    'VALIDATOR_FUNCTIONS',
    'VALIDATOR_SIGNATURES',
]
