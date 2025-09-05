from fastapi import HTTPException

def http_upstream_error(resp):
    detail = {"upstream_status": resp.status_code}
    try:
        detail["upstream_body"] = resp.json()
    except Exception:
        detail["upstream_body"] = resp.text
    raise HTTPException(status_code=502, detail=detail)
