from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
class Q0CompatibilityError(RuntimeError): pass
def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pointer(value,tokens):
    current=value
    for token in tokens:
        if not isinstance(current,dict) or token not in current:
            raise Q0CompatibilityError(f"unresolved pointer:{tokens}")
        current=current[token]
    return current
def encode_keywords(value):
    if not isinstance(value,list) or not 1<=len(value)<=8:
        raise Q0CompatibilityError("keyword list")
    clean=[]
    for item in value:
        if not isinstance(item,str) or not item.strip() or len(item.strip())>64:
            raise Q0CompatibilityError("keyword item")
        item=item.strip()
        if any(mark in item for mark in (",","\n","\r")):
            raise Q0CompatibilityError("keyword delimiter")
        clean.append(item)
    encoded=", ".join(clean)
    if encoded.split(", ")!=clean: raise Q0CompatibilityError("keyword roundtrip")
    return encoded
def materialize(handoff_path,config_path,output_path):
    handoff_path=Path(handoff_path); config=json.loads(Path(config_path).read_text())
    if sha256(handoff_path)!=config["q0_handoff_sha256"]:
        raise Q0CompatibilityError("handoff hash")
    handoff=json.loads(handoff_path.read_text()); row={}
    for column,spec in config["bindings"].items():
        value=spec["value"] if spec["kind"]=="literal" else pointer(handoff,spec["pointer"])
        if spec.get("codec")=="comma_space_join_v1": value=encode_keywords(value)
        if not isinstance(value,(str,int,float,bool)) or not str(value).strip():
            raise Q0CompatibilityError(column)
        row[column]=value
    if config["columns"]!=["image_id","image_path","response"]:
        raise Q0CompatibilityError("columns")
    output=Path(output_path); output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(".csv.tmp")
    with temporary.open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=config["columns"])
        writer.writeheader(); writer.writerow(row)
    temporary.replace(output)
    return {"schema":"tracehoi.LegacyKeywordCSVReceipt.v4","path":str(output),
      "sha256":sha256(output),"rows":1,"response":row["response"],
      "api_calls":0,"gpu_updates":0,"decision":"legacy_keyword_CSV_materialized"}
