from __future__ import annotations
import argparse,json
from pathlib import Path
from foho.automation.foundation_terminal_contract import sha,validate_foundation_terminal
from foho.automation import gate_a_adapter
from foho.automation.pilot_dag import RestartableCaseDAG

STAGES=("gate_a","frame_i","gate_c","d0","h0","h1","o0","j0","f0","final_export","evaluation")
def load_config(path):
    packet=json.loads(Path(path).read_text())
    if packet.get("schema")!="tracehoi.PostQ2Config.v1": raise RuntimeError("post-Q2 config schema")
    if tuple(packet.get("stage_order",()))!=STAGES: raise RuntimeError("post-Q2 stage order")
    return packet
def make_dag(config,run_root):
    return RestartableCaseDAG(config["case_id"],run_root,config["owner_bundle"],config["roots"],stage_order=STAGES)
def plan(config_path):
    config=load_config(config_path)
    return {"schema":"tracehoi.PostQ2Plan.v1","case_id":config["case_id"],
      "accepted_terminal_schemas":["tracehoi.FoundationTerminalPass.v1","tracehoi.Q2TerminalResult.v1"],
      "stage_order":list(STAGES),"execution":"mock_only",
      "decision":"post_Q2_plan_closed"}
def status(config_path,run_root):
    config=load_config(config_path); return make_dag(config,run_root).resume()
def run_mock(config_path,foundation_result,run_root,max_stages=None):
    config=load_config(config_path); accepted=validate_foundation_terminal(foundation_result)
    if accepted.get("case_id")!=config["case_id"]:
        raise RuntimeError("foundation terminal case mismatch")
    dag=make_dag(config,run_root)
    source=Path(foundation_result).resolve()
    state=dag.start({"foundation_terminal":{"path":str(source),"sha256":sha(source)}})
    count=0
    while int(state["next_index"])<len(STAGES) and (max_stages is None or count<max_stages):
        stage=STAGES[int(state["next_index"])]
        def producer(stage_root,inputs,stage=stage):
            out=stage_root/(stage+"_mock.json")
            out.write_text(json.dumps({"schema":"tracehoi.PostQ2MockArtifact.v1",
              "stage":stage,"inputs":inputs},sort_keys=True)+"\n")
            return {stage:str(out)}
        dag.run_stage(stage,producer); state=dag.resume(); count+=1
    return state
def run_real_gate_a(config_path,gate_a_config,foundation_result,run_root):
    config=load_config(config_path); accepted=validate_foundation_terminal(foundation_result)
    if accepted.get("case_id")!=config["case_id"]:
        raise RuntimeError("foundation terminal case mismatch")
    dag=make_dag(config,run_root); source=Path(foundation_result).resolve()
    state=dag.start({"foundation_terminal":{"path":str(source),"sha256":sha(source)}})
    if int(state["next_index"])!=0:
        if state["history"] and state["history"][0]["stage"]=="gate_a": return state
        raise RuntimeError("real Gate-A can only own the first downstream stage")
    def producer(stage_root,inputs):
        terminal=gate_a_adapter.run(gate_a_config,source,stage_root/"gate_a_runtime")
        terminal_path=stage_root/"gate_a_runtime"/"gate_a_terminal.json"
        if terminal.get("eligible_for_frame_i") is not True: raise RuntimeError("Gate-A is not eligible for frame I")
        return {"gate_a_terminal":str(terminal_path)}
    dag.run_stage("gate_a",producer)
    return dag.resume()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("mode",choices=("plan","status","mock","resume","gate-a-plan","gate-a-run","gate-a-resume","gate-a-audit"))
    parser.add_argument("--config",required=True); parser.add_argument("--run-root")
    parser.add_argument("--gate-a-config")
    parser.add_argument("--foundation-pass"); parser.add_argument("--q2-result")
    parser.add_argument("--max-stages",type=int); args=parser.parse_args()
    if args.mode=="plan": result=plan(args.config)
    elif args.mode=="status": result=status(args.config,args.run_root)
    else:
        supplied=[value for value in (args.foundation_pass,args.q2_result) if value]
        if len(supplied)!=1:
            raise RuntimeError("supply exactly one of --foundation-pass or --q2-result")
        if args.mode in ("mock","resume"):
            result=run_mock(args.config,supplied[0],args.run_root,args.max_stages)
        else:
            if not args.gate_a_config: raise RuntimeError("--gate-a-config is required")
            gate_root=Path(args.run_root)/"00_gate_a"/"gate_a_runtime"
            if args.mode=="gate-a-plan": result=gate_a_adapter.plan(args.gate_a_config,supplied[0],gate_root)
            elif args.mode=="gate-a-audit": result=gate_a_adapter.audit(args.gate_a_config,supplied[0],gate_root)
            else: result=run_real_gate_a(args.config,args.gate_a_config,supplied[0],args.run_root)
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__": main()
