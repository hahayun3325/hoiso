# Phase 0.17 — Weekly Comparison Tables

## Table 1 — Prompt Template Ablation

| Dataset | Input | Prompt source | Prompt detail | Inpaint result | Hunyuan result | Final result | Main lesson |
|---|---|---|---|---|---|---|---|
| HO3D | SPAM can | Default Gemini | vague / generic | rounded can body | weak object prior | rounded or incorrect object | Vague prompt causes semantic drift |
| HO3D | SPAM can | Structured template | boxy SPAM tin, rectangular body, not cylindrical | better boxy object | better object prior | final guidance can fragment object | Prompt helps, but later guidance still needs control |
| OakInk | split000 | Default Gemini | "A spray bottle" | hybrid bottle/spray object | ambiguous object | selector chooses final object | Official dataset also shows prompt sensitivity |
| ARCTIC | box_grab_01 | Manual LLM template | TBD | TBD | TBD | TBD | Good rigid prompt test |
| ARCTIC | ketchup_grab_01 | Manual LLM template | TBD | TBD | TBD | TBD | Good bottle/cylinder ambiguity test |

## Table 2 — Selector Decision

| Dataset | Input | Initial object | Final object | Selector output | Interpretation |
|---|---|---|---|---|---|
| HO3D | SPAM smoke015–022 | more complete initial object | fragmented final object | fallback / Hunyuan | Selector protects object geometry |
| OakInk | split000 | comp=3, frag=2.095 | comp=2, frag=1.047 | final object | Selector is not blindly choosing Hunyuan |
| ARCTIC | scissors_grab_01 | TBD | TBD | TBD | Thin-object stress test |
| ARCTIC | laptop_use_01 | TBD | TBD | TBD | Articulated-object stress test |
| ARCTIC | microwave_use_01 | TBD | TBD | TBD | Articulated-object stress test |

## Table 3 — Candidate Inputs

| Purpose | Dataset | Candidate | Camera angle | Frame | Why |
|---|---|---|---:|---:|---|
| Prompt sensitivity | ARCTIC | box_grab_01 | from split | 82 / 310 | boxy rigid object |
| Prompt sensitivity | ARCTIC | ketchup_grab_01 | from split | 147 / 236 | bottle-like ambiguity |
| Selector stress | ARCTIC | scissors_grab_01 | from split | 365 / 473 | thin structure |
| Articulation | ARCTIC | laptop_use_01 | 0 | 114 | opening laptop |
| Articulation | ARCTIC | microwave_use_01 | 0 | 152 | opening microwave door |
| Official smoke | OakInk | split000 | N/A | N/A | already ran successfully |
| Official smoke | DexYCB | subject-01 first split | camera-specific | color_000060 | subject-01 subset ready |
