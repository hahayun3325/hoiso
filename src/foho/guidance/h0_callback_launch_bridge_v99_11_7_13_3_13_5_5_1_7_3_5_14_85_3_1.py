import inspect

def invoke_callback_capable_target(target, callback, keyword_arguments):
    if not callable(target) or not callable(callback):
        raise TypeError('target_and_callback_must_be_callable')
    if not isinstance(keyword_arguments,dict):
        raise TypeError('keyword_arguments_must_be_dictionary')
    if 'h0_live_callback' in keyword_arguments:
        raise ValueError('callback_must_not_be_supplied_twice')
    signature=inspect.signature(target)
    parameter=signature.parameters.get('h0_live_callback')
    if parameter is None or parameter.default is not None or parameter.kind is not inspect.Parameter.KEYWORD_ONLY:
        raise TypeError('target_must_expose_default_None_keyword_only_h0_live_callback')
    return target(h0_live_callback=callback,**dict(keyword_arguments))
