from __future__ import annotations
from foho.guidance import j0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_100_2 as owner

def main():
    runtime=object(); bind_calls=[]; run_calls=[]
    def binder(context):
        bind_calls.append(context)
        bound=dict(context); bound['j0_runtime']=runtime
        return bound
    original=owner.run_live
    def fake_run_live(actual_runtime,**kwargs):
        run_calls.append((actual_runtime,kwargs))
        return {'updates_completed':0,'gradient_stats':{'global_hand_rotation':1.0},'trajectory':[]}
    owner.run_live=fake_run_live
    callback=owner.BoundJ0Callback(binder,0,True,False)
    raw={'sentinel':'raw_context'}; caught=None
    try:
        callback(raw)
    except owner.J0DiagnosticComplete as complete:
        caught=complete.outcome
    finally:
        owner.run_live=original
    assert caught and caught['handled'] is True
    assert caught['result']['updates_completed']==0
    assert len(bind_calls)==1 and bind_calls[0] is raw
    assert len(run_calls)==1 and run_calls[0][0] is runtime
    assert run_calls[0][1]=={'attempts':0,'checkpoint_every':1,'backward_only':True,'capture_only':False}
    try:
        callback.bind_live_context(raw)
    except RuntimeError as exc:
        assert str(exc)=='J0_context_may_be_bound_once'
    else:
        raise AssertionError('second_binding_was_not_rejected')
    print('pass_J0_callback_lifecycle_CPU')

if __name__=='__main__': main()
