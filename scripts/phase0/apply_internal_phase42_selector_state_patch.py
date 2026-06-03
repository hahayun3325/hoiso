from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

if "FOHO_INTERNAL_PHASE42_SELECTOR_STATE_PATCH" in s:
    print("[OK] patch already applied")
    raise SystemExit(0)

# 1. Add selector state variables after object transform initialization.
anchor_init = "        rotation_obj = torch.tensor([1.0, 0.0, 0.0, 0.0], device=device) # quaternion wxyz\n"
insert_init = anchor_init + """
        # FOHO_INTERNAL_PHASE42_SELECTOR_STATE_PATCH
        # Store object states so an internal selector can choose which state enters joint alignment.
        foho_obj_state_before_phase42 = None
        foho_phase42_selector_applied = False
"""

if anchor_init not in s:
    raise RuntimeError("Could not find object transform initialization anchor.")

s = s.replace(anchor_init, insert_init, 1)

# 2. Save state before object-only optimization.
anchor_obj = "                        info_str = f'Object optimization step {i}, optimizing object transformation'\n"
insert_obj = """                        if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and foho_obj_state_before_phase42 is None:
                            foho_obj_state_before_phase42 = {
                                "scale_obj": scale_obj.clone().detach(),
                                "trans_obj": trans_obj.clone().detach(),
                                "rotation_obj": rotation_obj.clone().detach(),
                                "obj_latents": obj_latents.clone().detach(),
                            }
                            print(f"[FOHO_INTERNAL_SELECTOR] saved before_phase42 state at step {i}")
""" + anchor_obj

if anchor_obj not in s:
    raise RuntimeError("Could not find object optimization anchor.")

s = s.replace(anchor_obj, insert_obj, 1)

# 3. Apply selector before joint optimization.
anchor_joint = "                        info_str = f'Joint optimization step {i}, optimizing hands and object together'\n"
insert_joint = """                        if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and not foho_phase42_selector_applied:
                            choice = os.environ.get("FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "phase42_before_joint")

                            if choice in ["before_phase42", "pre_phase42", "initial"]:
                                if foho_obj_state_before_phase42 is None:
                                    print("[FOHO_INTERNAL_SELECTOR] before_phase42 state missing; keeping phase42_before_joint")
                                    selected_name = "phase42_before_joint"
                                else:
                                    scale_obj = foho_obj_state_before_phase42["scale_obj"].clone().to(device)
                                    trans_obj = foho_obj_state_before_phase42["trans_obj"].clone().to(device)
                                    rotation_obj = foho_obj_state_before_phase42["rotation_obj"].clone().to(device)
                                    obj_latents = foho_obj_state_before_phase42["obj_latents"].clone().to(device)
                                    selected_name = "before_phase42"
                            elif choice in ["phase42_before_joint", "phase42", "current"]:
                                selected_name = "phase42_before_joint"
                            else:
                                selected_name = "phase42_before_joint"
                                print(f"[FOHO_INTERNAL_SELECTOR] unknown choice={choice}; keeping phase42_before_joint")

                            foho_phase42_selector_applied = True
                            print(f"[FOHO_INTERNAL_SELECTOR] selected={selected_name}; applied before joint step {i}")
""" + anchor_joint

if anchor_joint not in s:
    raise RuntimeError("Could not find joint optimization anchor.")

s = s.replace(anchor_joint, insert_joint, 1)

p.write_text(s)
print("[OK] applied internal Phase 4.2 selector state patch")
