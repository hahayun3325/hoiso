from __future__ import annotations
import ast,importlib.util,json,os,tempfile
from pathlib import Path
import torch

target=Path(os.environ["O0_PANEL_BINDING_TARGET"])
spec=importlib.util.spec_from_file_location("_o0_panel_binding_target",target)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
errors=[]; checks={}
try:
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory); policy=root/"policy.json"; manifest=root/"manifest.json"
        policy.write_text("{}\n"); manifest.write_text(json.dumps({"paths":{"o0_policy":str(policy)}})+"\n")
        resources={"sentinel":"same_loaded_resources"}; calls=[]
        def fake_load(paths,device,dtype):
            calls.append(("load",paths,device,dtype)); return resources
        def fake_bind(context,actual_resources,output_root,actual_policy):
            calls.append(("bind",actual_resources,Path(output_root),actual_policy))
            bound=dict(context); bound["current_object_mesh"]=lambda:"GateA_live_mesh"; return bound
        module.load_o0_resources=fake_load; module.bind_o0_live_context=fake_bind
        callback=module.O0ReadOnlyPanelCallback(manifest,root/"checkpoint.pt",root/"evaluation.json",root/"rgb.png",root/"panel.png",root/"receipt.json")
        rotation=torch.tensor([1.0,0.0,0.0,0.0]); translation=torch.zeros(3)
        context={"parameters":{"global_object_rotation":rotation,"global_object_translation":translation},"frozen":{},"rendering":{},"metadata":{"GateA_object_owned_by_binder":True}}
        bound=callback.bind_live_context(context)
        source=target.read_text()
        tree=ast.parse(source)
        forbidden_optimizer_actions=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                func=node.func
                terminal=func.attr if isinstance(func,ast.Attribute) else (func.id if isinstance(func,ast.Name) else "")
                if terminal in {"backward","step","zero_grad","Adam","AdamW","SGD","RMSprop","Adagrad"}:
                    forbidden_optimizer_actions.append(terminal)
            if isinstance(node,ast.ImportFrom) and str(node.module or "").startswith("torch.optim"):
                forbidden_optimizer_actions.append(str(node.module))
            if isinstance(node,ast.Import) and any(alias.name.startswith("torch.optim") for alias in node.names):
                forbidden_optimizer_actions.append("torch.optim")
        checks={
          "canonical_binder_called_once":len([row for row in calls if row[0]=="bind"])==1,
          "same_resources_loaded_and_cached":callback._bound_resources is resources and calls[1][1] is resources,
          "dynamic_mesh_owner_reaches_panel":callable(bound.get("current_object_mesh")) and bound["current_object_mesh"]()=="GateA_live_mesh",
          "parameters_are_same_objects":bound["parameters"]["global_object_rotation"] is rotation and bound["parameters"]["global_object_translation"] is translation,
          "panel_binds_before_owner_reads":"context = self.bind_live_context(context)" in source and source.index("context = self.bind_live_context(context)")<source.index("current_object_mesh = context.get"),
          "panel_reuses_bound_resources":"resources = self._bound_resources" in source,
          "panel_has_no_optimizer_or_backward":not forbidden_optimizer_actions,
        }
except Exception as exc:
    errors.append(f"{type(exc).__name__}:{exc}")
failed=[name for name,value in checks.items() if not value]
payload={"decision":("pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_2_3_O0_panel_live_owner_CPU_closed" if not failed and not errors else "review_required_14_99_2_3_O0_panel_live_owner_CPU"),"checks":checks,"failed":failed,"errors":errors,"GPU_used":False,"optimizer_updates":0}
print(json.dumps(payload))
