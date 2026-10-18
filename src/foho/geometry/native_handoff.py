"""Opt-in native handoff for a saved visual initializer.

The adapter compiles a private copy of the pinned backend call. Installed native
sources and the original pipeline class are never changed. Building a packet
does not import torch or execute a model. Native execution still needs the
matching fresh-scene inputs and a separately checked runtime configuration.
"""
import ast
import copy
import hashlib
import html
import inspect
import json
import os
import textwrap
from pathlib import Path

PURPOSE = 'native_handoff'
CLASS = 'Hunyuan3DDiTFlowMatchingPipeline_main'
BACKEND_PINS = (
    '30e20924ac044cb46bec3f3c75aa9bb4f914724a3a3347c4c3c411a26b84b6c7',
    '129b6828b539b34dc06f65495a61f57bd1cc1aa6559e884a30c04552a95ab4d8',
)
BACKEND_PATHS = ('third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py',
                 'third_party/utilz/code_utils.py')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def pin(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def backend_function(raw):
    tree = ast.parse(raw)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == CLASS]
    require(len(classes) == 1, 'native_class')
    functions = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == '__call__']
    require(len(functions) == 1, 'native_call')
    return functions[0]


def patch_source(raw):
    """Only four reviewed seams change; all other bytes remain identical."""
    require(pin(raw)['sha256'] == BACKEND_PINS[0], 'backend_source_changed')
    source = raw.decode()
    edits = [
        ('*, h0_live_callback=None, o0_live_callback=None, j0_live_callback=None, **kwargs,',
         '*, h0_live_callback=None, o0_live_callback=None, j0_live_callback=None, _tracehoi_handoff=None, **kwargs,'),
        ('mano_verts, mano_faces = load_ply(aligned_mano_mesh_path)',
         'mano_verts, mano_faces = load_ply(_tracehoi_handoff.mesh_path if _tracehoi_handoff is not None else aligned_mano_mesh_path)'),
        ('        mano_mesh_moge = transform_hunyuan2moge(mano_mesh, T_h2m)',
         '        if _tracehoi_handoff is None:\n'
         '            mano_mesh_moge = transform_hunyuan2moge(mano_mesh, T_h2m)\n'
         '        else:\n'
         '            mano_mesh_moge = mano_mesh\n'
         '            scale_hand, trans_hand, rotation_hand = _tracehoi_handoff.tensors(mano_mesh, torch, device)'),
        ('                    if _foho_f3_enabled and i == handopt_start_step:',
         '                    if _tracehoi_handoff is not None and i in (handopt_start_step, handopt_start_step + 1):\n'
         '                        pass  # Keep the visual hand and supplied object placement until joint guidance.\n'
         '                    elif _foho_f3_enabled and i == handopt_start_step:'),
    ]
    for before, after in edits:
        require(source.count(before) == 1, 'native_seam_changed')
        source = source.replace(before, after, 1)
    ast.parse(source)
    return source.encode()


def source_checks(pipeline_raw, helper_raw):
    require(pin(helper_raw)['sha256'] == BACKEND_PINS[1], 'guidance_helper_changed')
    patched = patch_source(pipeline_raw)
    return dict(original=pin(pipeline_raw), helper=pin(helper_raw), overlay=pin(patched),
                installed_sources_modified=False, private_call_only=True,
                changes=['explicit_opt_in_argument', 'native_hand_mesh_route',
                         'saved_centered_state_and_hand_frame_bypass', 'skip_legacy_initialization_phases']), patched


def cpu_transition_probe(pipeline_raw, helper_raw, state, vertices, faces):
    """Execute actual changed seam and phase helper ASTs using CPU test doubles.

    This verifies branch/state wiring without importing the native stack. It is
    deliberately reported separately from native tensor or model validation.
    """
    _, overlay = source_checks(pipeline_raw, helper_raw)
    tree = ast.parse(overlay)

    class Tensor:
        def __init__(self, value): self.value=copy.deepcopy(value); self.grad=False
        def clone(self): return Tensor(self.value)
        def detach(self): return self
        def requires_grad_(self, flag): self.grad=flag; return self
        def cpu(self): return self
        def tolist(self): return copy.deepcopy(self.value)

    class Torch:
        float32='float32'
        @staticmethod
        def tensor(value, **kwargs): return Tensor(value)

    class Mesh:
        def verts_packed(self): return Tensor(vertices)
        def faces_packed(self): return Tensor(faces)

    hand = _HandState('.',state,vertices,faces)
    seams=[n for n in ast.walk(tree) if isinstance(n,ast.If) and
           ast.unparse(n.test)=='_tracehoi_handoff is None']
    require(len(seams)==1,'probe_state_seam')
    transformations=[]
    def legacy(mesh,T): transformations.append(T); return 'legacy_mesh'
    def execute(node,env):
        exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(node)],type_ignores=[])),
                     '<CPU native seam probe>','exec'),env)
    mesh=Mesh()
    env=dict(_tracehoi_handoff=hand,mano_mesh=mesh,T_h2m='object_transform',
             transform_hunyuan2moge=legacy,torch=Torch,device='cpu')
    execute(seams[0],env)
    require(env['mano_mesh_moge'] is mesh and not transformations,'probe_double_transform')
    expected=[state['scale']],state['translation'],state['rotation_wxyz']
    require([env[k].value for k in ('scale_hand','trans_hand','rotation_hand')]==list(expected),'probe_state_consumption')
    legacy_env=dict(env,_tracehoi_handoff=None)
    execute(seams[0],legacy_env)
    require(legacy_env['mano_mesh_moge']=='legacy_mesh' and transformations==['object_transform'],'probe_default_path')
    routes=[n for n in ast.walk(tree) if isinstance(n,ast.If) and
            ast.unparse(n.test).startswith('_tracehoi_handoff is not None and i in')]
    require(len(routes)==1,'probe_phase_seam')
    def route(step,enabled):
        node=routes[0]; e=dict(i=step,handopt_start_step=10,guidance_end_step=20,_tracehoi_handoff=hand if enabled else None,_foho_f3_enabled=False)
        while isinstance(node,ast.If):
            if eval(compile(ast.Expression(node.test),'<CPU phase probe>','eval'),e):
                if isinstance(node.body[0],ast.Pass):return 'skip'
                if 'guidance_end_step' in ast.unparse(node.test):return 'joint'
                return ast.unparse(node.test)
            node=node.orelse[0] if len(node.orelse)==1 and isinstance(node.orelse[0],ast.If) else None
        return 'joint'
    require([route(i,True) for i in (10,11,12)]==['skip','skip','joint'],'probe_phase_route')
    require(route(10,False)=='i == handopt_start_step' and route(11,False)=='i == handopt_start_step + 1','probe_default_phase_route')
    helper=next(n for n in ast.parse(helper_raw).body if isinstance(n,ast.FunctionDef))
    helper_env=dict(torch=Torch);execute(helper,helper_env)
    values=[Tensor([.1,.2]),env['scale_hand'],env['trans_hand'],env['rotation_hand']]
    obj=[Tensor([1.]),Tensor([0.,0.,0.]),Tensor([1.,0.,0.,0.])]
    out=helper_env['get_guidance_params'](2,*values,'cpu',phase1_hand_lrs={'scale':1,'trans':2,'rot':3},
          phase2_hand_lrs={'scale':4,'trans':5,'rot':6},noise_obj_lr1=7,noise_obj_lr2=8,
          obj_lrs={'scale':9,'trans':10,'rot':11},obj_2half_lrs={'scale':12,'trans':13,'rot':14},
          scale_obj=obj[0],trans_obj=obj[1],rotation_obj=obj[2])
    require([x.value for x in out[1:]]==[x.value for x in values+obj],'probe_joint_reset')
    require(all(a is not b and a.grad for a,b in zip(out[1:],values+obj)),'probe_joint_clone')
    require(len(out[0])==7 and all(out[0][i]['params'][0] is out[j] for i,j in enumerate([2,3,4,5,6,7,1])),'probe_optimizer_ownership')
    return dict(test_doubles_used=True,native_tensor_execution=False,
                saved_state_consumed=True,hand_frame_conversion_bypassed=True,
                legacy_default_preserved=True,legacy_initialization_skipped=True,
                joint_parameter_values_preserved=True,joint_parameter_groups=7)


def bridge_files(folder, sha, reader):
    folder = Path(folder)
    raw = reader.regular(folder/'files.json', 1024**2)
    require(pin(raw)['sha256'] == sha, 'bridge_receipt_binding')
    members = json.loads(raw)['members']
    expected = {'index.html','bridge.json','centered_state.json','baked_state.json',
                'native_hand.ply','hand_initial.ply','object.ply','scene.html',
                'initialization.json','optimizer_input.json','image.png','README.md'}
    require(set(members) == expected, 'bridge_inventory')
    files = {n:reader.regular(folder/n, 16*1024**2) for n in members}
    require({n:pin(b) for n,b in files.items()} == members, 'bridge_member_binding')
    files['files.json'] = raw
    return files


def build(folder, sha, pipeline_raw, helper_raw, reader, bridge, *, purpose):
    require(purpose == PURPOSE, 'native_handoff_purpose_required')
    files = bridge_files(folder, sha, reader)
    state = json.loads(files['centered_state.json'])
    report = json.loads(files['bridge.json'])
    require(report['bridge_complete'] is True and report['initialization_ready'] is True and
            report['contact_terms_used'] is False, 'bridge_not_ready')
    require(state == report['native_state'], 'state_binding')
    vertices, faces = reader.mesh(files['native_hand.ply'])
    vertices = [list(v) for v in vertices]
    # PLY is float32; the pinned prediction's JSON preserves those exact values.
    placed = bridge.apply_state(vertices, state, input_geometry='native_hamer',
                                geometry_binding=state['input_geometry_binding'])
    expected, ef = reader.mesh(files['hand_initial.ply'])
    require(len(vertices) == 778 and len(faces) == 1538 and faces == ef, 'hand_topology')
    error = max(abs(a-b) for p,q in zip(placed,expected) for a,b in zip(p,q))
    require(error < 1e-6, 'handoff_pose_changed')
    checks, overlay = source_checks(pipeline_raw, helper_raw)
    probe=cpu_transition_probe(pipeline_raw,helper_raw,state,vertices,[list(f) for f in faces])
    r = dict(schema='tracehoi.NativeHandoff.v1', case_id=report['case_id'],
             native_handoff_complete=True, initialization_ready=True,
             native_handoff_wired=True, backend_execution_ready=False,
             native_execution_verified=False, rectified_flow_executed=False,
             contact_terms_used=False, model_calls=0, source_meshes_modified=False,
             placement_ready=False, full_parent_acceptance=False,
             mask_accuracy_verified=False, reference_status='awaiting_reference',
             source_receipt_sha256=sha, source_checks=checks, cpu_transition_probe=probe, max_pose_error=error,
             initial_state=state, hand_geometry='native_hamer',
             phase_policy={'1':'skip_visual_initialization_already_complete',
                           '1.5':'skip_preserve_supplied_object_placement',
                           '2':'existing_joint_rectified_flow_guidance'},
             next_action='validate_native_camera_masks_object_transform_and_runtime_assets',
             runtime_pending=['fresh_scene_camera_and_renderer', 'exact_hand_and_object_masks',
                              'object_hunyuan_to_fresh_scene_transform', 'HaMeR_guidance_asset',
                              'native_tensor_and_model_preflight', 'bounded_rectified_flow_run'])
    payload = {n:files[n] for n in ['centered_state.json','native_hand.ply','hand_initial.ply',
                'object.ply','scene.html','initialization.json','optimizer_input.json','image.png']}
    payload.update({'handoff.json':encode(r), 'pipeline_overlay.py.txt':overlay,
                    'guidance_helper.py.txt':helper_raw, 'bridge.json':files['bridge.json']})
    payload['index.html'] = viewer(r).encode()
    payload['README.md'] = b'# TraceHOI native handoff\n\nOpen index.html. The opt-in adapter preserves the visual hand state and skips legacy initialization. Contact belongs to subsequent joint rectified-flow optimization. Native execution has not been validated or run. Keep all companion files and original evidence.\n'
    payload['files.json'] = encode(dict(schema='tracehoi.NativeHandoffFiles.v1', members={n:pin(b) for n,b in payload.items()}))
    return r, payload


def verify(folder, receipt_sha, source, source_sha, pipeline_raw, helper_raw, reader, bridge, *, purpose):
    r, files = build(source, source_sha, pipeline_raw, helper_raw, reader, bridge, purpose=purpose)
    require(pin(files['files.json'])['sha256'] == receipt_sha, 'receipt_binding')
    folder = Path(folder)
    require(set(p.name for p in folder.iterdir()) == set(files), 'output_inventory')
    for n,b in files.items():
        require(reader.regular(folder/n,16*1024**2) == b, 'output_changed:'+n)
    return dict(verified=True,receipt_binding=pin(files['files.json']),
                initialization_ready=True,native_handoff_complete=True,
                backend_execution_ready=False,placement_ready=False)


class _HandState:
    def __init__(self, folder, state, native, faces):
        self.mesh_path = str(Path(folder).resolve()/'native_hand.ply')
        self.state = copy.deepcopy(state)
        self.native = native
        self.faces = faces

    def tensors(self, mesh, torch, device):
        # Validate the mesh actually loaded by PyTorch3D, before using the state.
        vertices = mesh.verts_packed().detach().cpu().tolist()
        faces = mesh.faces_packed().detach().cpu().tolist()
        require(vertices == self.native and faces == self.faces, 'runtime_native_mesh_changed')
        s = self.state
        return (torch.tensor([s['scale']], dtype=torch.float32, device=device),
                torch.tensor(s['translation'], dtype=torch.float32, device=device),
                torch.tensor(s['rotation_wxyz'], dtype=torch.float32, device=device))


def _function_ast(function):
    node = ast.parse(textwrap.dedent(inspect.getsource(inspect.unwrap(function)))).body[0]
    node.decorator_list = []
    return ast.dump(node, include_attributes=False)


def bind_pipeline(pipeline, folder, receipt_sha, source, source_sha, repo, reader, bridge):
    """Return a callable opt-in adapter; never mutate the instance or globals.

    This API is a wiring seam, not a runnable experiment recipe. The caller must
    provide and validate native camera, image, mask, object-transform and guidance
    assets. No model is invoked by binding. The actual call enters the existing
    rectified-flow loop and is therefore a separate execution step.
    """
    repo = Path(repo)
    raw = reader.regular(repo/BACKEND_PATHS[0],2*1024**2)
    helper = reader.regular(repo/BACKEND_PATHS[1],2*1024**2)
    verify(folder,receipt_sha,source,source_sha,raw,helper,reader,bridge,purpose=PURPOSE)
    original = inspect.unwrap(type(pipeline).__call__)
    require(Path(inspect.getfile(original)).resolve() == (repo/BACKEND_PATHS[0]).resolve(), 'runtime_backend_origin')
    original_ast = backend_function(raw)
    original_ast.decorator_list = []
    require(_function_ast(original) == ast.dump(original_ast,include_attributes=False), 'runtime_backend_call_changed')
    guidance = original.__globals__['get_guidance_params']
    require(Path(inspect.getfile(guidance)).resolve() == (repo/BACKEND_PATHS[1]).resolve(), 'runtime_helper_origin')
    helper_ast = next(n for n in ast.parse(helper).body if isinstance(n,ast.FunctionDef))
    require(_function_ast(guidance) == ast.dump(helper_ast,include_attributes=False), 'runtime_helper_changed')
    fn = backend_function(patch_source(raw))
    # Keep native @torch.no_grad and annotations, using a private globals mapping.
    module = ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
    namespace = dict(original.__globals__)
    exec(compile(module,'<TraceHOI native handoff>', 'exec'),namespace)
    private_call = namespace['__call__']
    folder = Path(folder)
    state = json.loads(reader.regular(folder/'centered_state.json',1024**2))
    v,f = reader.mesh(reader.regular(folder/'native_hand.ply',1024**2))
    hand = _HandState(folder,state,[list(x) for x in v],[list(x) for x in f])

    def call(*args, **kwargs):
        # The current native signature has positional optional arguments. Require
        # keyword calls so an incompatible hand path cannot hide in *args.
        require(not args, 'native_handoff_keyword_arguments_required')
        require('_tracehoi_handoff' not in kwargs, 'internal_handoff_override')
        require(all(kwargs.get(k) is None for k in ('h0_live_callback','o0_live_callback','j0_live_callback')), 'legacy_callback_conflict')
        require(not any(k.startswith('FOHO_') and v for k,v in os.environ.items()), 'legacy_environment_conflict')
        require(kwargs.get('aligned_mano_mesh_path') in (None,hand.mesh_path), 'hand_path_conflict')
        # Recheck all packet and native bytes immediately before invocation.
        verify(folder,receipt_sha,source,source_sha,reader.regular(repo/BACKEND_PATHS[0],2*1024**2),
               reader.regular(repo/BACKEND_PATHS[1],2*1024**2),reader,bridge,purpose=PURPOSE)
        kwargs['aligned_mano_mesh_path'] = hand.mesh_path
        return private_call(pipeline,*args,_tracehoi_handoff=hand,**kwargs)
    return call


def viewer(r):
    data=json.dumps(r,sort_keys=True,separators=(',',':')).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>TraceHOI · Native handoff</title><style>body{margin:0;background:#091422;color:#e9f1fa;font:16px system-ui}main{max-width:1080px;margin:auto;padding:32px}h1{font-size:38px}p{color:#b5c8dc;line-height:1.6}a{color:#7ee6c7}section{background:#122338;border:1px solid #38536e;padding:24px;border-radius:16px;margin:20px 0}.steps{display:flex;gap:10px;flex-wrap:wrap}button{padding:14px;border:1px solid #53728c;border-radius:9px;color:#e9f1fa;background:#1d334c;font:inherit;cursor:pointer}button[aria-pressed=true]{background:#20705e}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px ui-monospace;line-height:1.6}.badge{color:#7ee6c7}.warn{color:#f2ce87}iframe{width:100%;height:640px;border:0;border-radius:12px}details{margin:16px 0}</style><main><span class="badge">TRACEHOI / VISUAL POSE → NATIVE GUIDANCE</span><h1>Start optimization from the visual pose.</h1><p>The hand scale and placement stay as initialized from the image, HaMeR, bounding box and fresh scene depth. Contact becomes an objective of the subsequent joint rectified-flow stage.</p><p class="warn">Adapter prepared and CPU tested. Native tensor execution and rectified-flow inference are still pending.</p><section><h2>Follow the stage transition</h2><div class="steps"><button data-stage="input" aria-pressed="true">1 · Saved pose</button><button data-stage="load" aria-pressed="false">2 · Native handoff</button><button data-stage="skip" aria-pressed="false">3 · Preserve placement</button><button data-stage="joint" aria-pressed="false">4 · Joint optimization</button></div><h3 id="title"></h3><p id="description"></p><pre id="state"></pre></section><section><h2>Inspect the unchanged initial scene</h2><p><a href="scene.html">Open the interactive scene ↗</a> · <a href="handoff.json">Handoff record</a> · <a href="pipeline_overlay.py.txt">Review the private source overlay</a></p><button id="load-scene">Load interactive scene</button><div id="scene"></div></section><section><h2>Runtime work remaining</h2><p>Before a native run, bind the fresh camera and renderer, exact masks, object transform and HaMeR guidance data. Then test native tensors and a bounded model run. The original backend class and installed source files are unchanged.</p><details><summary>Source bindings and checks</summary><pre id="checks"></pre></details><p>Independent mask accuracy, metric scale and final placement are not certified by this adapter.</p></section></main><script>const R=DATA,steps={input:['Saved visual initializer','Keep native hand articulation and the saved visual scale, rotation and translation.',{scale:R.initial_state.scale,rotation_wxyz:R.initial_state.rotation_wxyz,translation:R.initial_state.translation}],load:['Apply exactly one hand transform','Load native HaMeR vertices and centered parameters. Bypass the old hand Hunyuan-to-MoGe conversion.',{input:'native_hand.ply',state:'centered_state.json',frame:R.initial_state.output_frame}],skip:['Skip legacy initialization','Skip hand-only and object-only initialization branches so neither replaces the prepared starting scene.',R.phase_policy],joint:['Enter joint rectified-flow guidance','The existing guidance helper clones the incoming parameters without resetting their values. Contact optimization starts downstream; no such run has occurred here.',{native_execution_verified:false,rectified_flow_executed:false,backend_execution_ready:false}]};function show(k){let s=steps[k];document.getElementById('title').textContent=s[0];document.getElementById('description').textContent=s[1];document.getElementById('state').textContent=JSON.stringify(s[2],null,2);document.querySelectorAll('[data-stage]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.stage===k))}document.querySelectorAll('[data-stage]').forEach(b=>b.onclick=()=>show(b.dataset.stage));document.getElementById('checks').textContent=JSON.stringify(R.source_checks,null,2);document.getElementById('load-scene').onclick=function(){let f=document.createElement('iframe');f.title='Initialized hand and laptop';f.src='scene.html';document.getElementById('scene').replaceChildren(f);this.hidden=true};show('input');</script></html>'''.replace('DATA',data)
