import ast, importlib.util, json, os, subprocess
from pathlib import Path

root=Path(os.environ["PROJECT_ROOT"]); production=Path(os.environ["PRODUCTION_ENGINE"]); dispatcher_path=Path(os.environ["DISPATCH_SOURCE83"])
spec=importlib.util.spec_from_file_location("h0_dispatch83",dispatcher_path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
calls=[]
def false_callback(context): calls.append(context); return {"handled":False,"result":"legacy"}
def true_callback(context): calls.append(context); return {"handled":True,"result":"h0"}
def invalid_callback(context): calls.append(context); return {"handled":1}
def raising_callback(context): calls.append(context); raise RuntimeError("probe")
def simulate(callback):
    legacy_steps=0; outcome=module.dispatch_h0_live_callback(callback,{"sentinel":object()})
    if not outcome["handled"]: legacy_steps+=1
    return outcome,legacy_steps
none,none_steps=simulate(None); false,false_steps=simulate(false_callback); true,true_steps=simulate(true_callback)
invalid_raised=raising_raised=False
try: simulate(invalid_callback)
except TypeError: invalid_raised=True
try: simulate(raising_callback)
except RuntimeError: raising_raised=True

patched=production.read_text(); relative=str(production.relative_to(root)); original=subprocess.run(["git","show",f"HEAD:{relative}"],cwd=root,text=True,capture_output=True,check=True).stdout
def find_method(raw):
    tree=ast.parse(raw); cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Hunyuan3DDiTFlowMatchingPipeline_main"); return next(n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=="__call__")
def hand_loop(method,raw):
    loops=[n for n in ast.walk(method) if isinstance(n,ast.For) and "optimization_steps_hand" in (ast.get_source_segment(raw,n.iter) or ast.unparse(n.iter)).replace(" ","")]; assert len(loops)==1; return loops[0]
old_method=find_method(original); new_method=find_method(patched); old_loop=hand_loop(old_method,original)
guards=[n for n in ast.walk(new_method) if isinstance(n,ast.If) and ast.unparse(n.test).replace(" ","")=="noth0_handled"]
guard=guards[0] if len(guards)==1 else None; guarded_loops=[n for n in (guard.body if guard else []) if isinstance(n,ast.For)]; guarded_loop=guarded_loops[0] if len(guarded_loops)==1 else None
all_args=[*new_method.args.posonlyargs,*new_method.args.args,*new_method.args.kwonlyargs]; arg_names=[a.arg for a in all_args]
signature_text=ast.unparse(new_method.args).replace(" ","")
callback_ifs=[n for n in ast.walk(new_method) if isinstance(n,ast.If) and "h0_live_callback is not None" in ast.unparse(n.test)]
callback_calls=[n for n in ast.walk(new_method) if isinstance(n,ast.Call) and ((isinstance(n.func,ast.Name) and n.func.id=="dispatch_h0_live_callback") or (isinstance(n.func,ast.Name) and n.func.id=="h0_live_callback"))]
hand_steps=[n for n in ast.walk(new_method) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="step" and ast.unparse(n.func.value)=="hand_optimizer"]
checks={
 "dispatcher_none":none=={"handled":False,"result":None} and none_steps==1,
 "dispatcher_false":false_steps==1 and false["result"]=="legacy",
 "dispatcher_true":true_steps==0 and true["result"]=="h0",
 "invalid_literal_bool_rejected":invalid_raised,
 "callback_exception_propagates":raising_raised,
 "callback_argument_exists":arg_names.count("h0_live_callback")==1,
 "callback_is_keyword_only":[a.arg for a in new_method.args.kwonlyargs].count("h0_live_callback")==1,
 "callback_default_is_None":"h0_live_callback=None" in signature_text,
 "one_callback_branch":len(callback_ifs)==1,
 "one_dispatch_call":len(callback_calls)==1,
 "one_hand_guard":guard is not None,
 "legacy_loop_AST_equivalent":guarded_loop is not None and ast.dump(old_loop,include_attributes=False)==ast.dump(guarded_loop,include_attributes=False),
 "one_guarded_hand_step":len(hand_steps)==1 and guard is not None and any(hand_steps[0] is child for child in ast.walk(guard)),
 "differentiable_base_loss_closure":"def _h0_compute_base_loss" in patched and "total_hand_loss" in patched,
}
payload={"decision":"pass_default_disabled_callback_CPU_and_source_tests" if all(checks.values()) else "review_required_default_disabled_callback_CPU_or_source_tests","checks":checks,"failed":[name for name,value in checks.items() if not value],"missing":[],"errors":[]}
print(json.dumps(payload))
