def dispatch_h0_live_callback(callback, live_context):
    if callback is None:
        return {"handled": False, "result": None}
    outcome = callback(live_context)
    if not isinstance(outcome, dict) or type(outcome.get("handled")) is not bool:
        raise TypeError("H0 callback must return a dict with literal-bool handled")
    return {"handled": outcome["handled"], "result": outcome.get("result")}
