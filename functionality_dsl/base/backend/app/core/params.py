from fastapi import Query

def pagination_params():
    return {
        "limit": Query(default=100, ge=1, le=1000),
        "offset": Query(default=0, ge=0),
        "sort": Query(default=None, description="field or -field"),
    }
