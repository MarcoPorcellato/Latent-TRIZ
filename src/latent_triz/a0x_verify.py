"""Independent fail-closed verification for immutable A0X terminal packages."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from latent_triz.validator import validate
from .a0x_contract import A0XContractError, LegFreezeBinding, PairBinding, assert_authorization_chain, assert_leg_freeze_binding, assert_pair_binding

class A0XVerificationError(ValueError): pass
_ROOT=Path(__file__).resolve().parents[2]
_SCHEMAS={"authorization_record":"a0x-execution-authorization.schema.json","model_identity_receipt":"a0x-model-identity-receipt.schema.json","ccp_observation":"a0x-ccp-observation.schema.json","preflight_receipt":"a0x-preflight-receipt.schema.json","activation_receipt":"a0x-activation-receipt.schema.json","target_read_receipt":"a0x-target-read-receipt.schema.json","statistical_result":"a0x-statistical-result.schema.json","terminal_result":"a0x-terminal-result.schema.json","external_assets_locator":"a0x-external-assets-locator.schema.json"}
_NO_CLAIM="This exploratory automated-proxy result is not a general TRIZ, causal, mechanism, emergence, or training-data claim."

def verify_a0x_package(*, package_root:str|Path, repository_root:str|Path, leg_freeze:LegFreezeBinding, dossier_path:str|Path, authorization_path:str|Path, expected_root_receipt_sha256:str, root_receipt_path:str|Path|None=None, protected_trees:Mapping[str,Mapping[str,Any]] | None=None, protected_tree_verifier:Callable[...,Any]|None=None)->None:
    pkg=_directory(Path(package_root),"package root"); repo=_directory(Path(repository_root),"repository root")
    manifest_path=_safe(pkg,"publication-manifest.json","manifest"); root_path=_safe(pkg,"output-occupancy-receipt.json","root")
    if root_receipt_path is not None and Path(root_receipt_path).resolve(strict=True)!=root_path.resolve(strict=True): raise A0XVerificationError("manifest root receipt path does not bind supplied root")
    manifest_raw,manifest=_json(manifest_path,"manifest"); root_raw,root=_json(root_path,"root")
    if _sha(root_raw)!=expected_root_receipt_sha256: raise A0XVerificationError("external root anchor differs")
    _validate(manifest,"a0x-publication-manifest.schema.json","manifest"); _validate(root,"a0x-output-occupancy-receipt.schema.json","root")
    if manifest.get("root_receipt_package_relative_path")!="output-occupancy-receipt.json": raise A0XVerificationError("manifest root path differs")
    pair=_pair(manifest)
    if _pair(root).as_mapping()!=pair.as_mapping() or root.get("authorization_chain")!=manifest.get("authorization_chain") or pair.leg is not leg_freeze.leg: raise A0XVerificationError("root/pair/freeze differs")
    if _safe_dir(repo,pair.output_path,"pair output").resolve(strict=True)!=pkg.resolve(strict=True): raise A0XVerificationError("package root differs from frozen PairBinding output path")
    dossier_raw,dossier=_json(_safe_repo(repo,Path(dossier_path),"dossier"),"dossier",strict=True); auth_raw,auth=_json(_safe_repo(repo,Path(authorization_path),"authorization"),"authorization",strict=True)
    try: assert_leg_freeze_binding(leg_freeze,[dossier])
    except A0XContractError as error: raise A0XVerificationError("leg freeze differs") from error
    ledgers={name:list(manifest[name]) for name in ("package_artifacts","external_outputs","source_inputs","retained_residue")}; _membership(pkg,ledgers)
    seen:set[tuple[str,int,int]]=set(); _unique(root_path,seen,"root"); _unique(manifest_path,seen,"manifest")
    values:dict[str,dict[str,Any]]={}; raws:dict[str,bytes]={}
    for e in ledgers["package_artifacts"]:
        role=e["role"]; path=_safe(pkg,e["path"],role); _unique(path,seen,role); raw=_read(path,role); value={"report":True} if role=="report" else _parse(raw,role)
        if len(raw)!=e["bytes"] or _sha(raw)!=e["raw_sha256"]: raise A0XVerificationError("artifact ledger differs")
        if role!="report":
            schema=_SCHEMAS.get(role)
            if schema is None: raise A0XVerificationError("unknown artifact role")
            _validate(value,schema,role)
            if _pair(value).as_mapping()!=pair.as_mapping() or (role!="authorization_record" and not isinstance(value.get("authorization_chain"),Mapping)): raise A0XVerificationError("artifact pair/chain differs")
        values[role]=value; raws[role]=raw
    _sources(repo,ledgers["source_inputs"],dossier_path,dossier_raw,authorization_path,auth_raw,raws,seen)
    _external(repo,ledgers["external_outputs"],values,pair,seen); _residue(repo,ledgers["retained_residue"],seen)
    _matrix(manifest,values,raws,leg_freeze); _root(root,root_raw,manifest_raw,ledgers,pair)
    try:
        graph=[manifest,root,*[v for k,v in values.items() if k not in {"authorization_record","report"}]]
        assert_authorization_chain(dossier,auth,graph)
        # The complete root is pair-scoped but has a different occupancy profile
        # from the reservation receipt recognized by the legacy contract helper.
        root_pair_view=dict(root); root_pair_view["artifact_class"]="a0x-complete-attempt-root-binding"
        assert_pair_binding(pair,[manifest,root_pair_view,*[v for k,v in values.items() if k not in {"authorization_record","report"}]])
    except A0XContractError as error: raise A0XVerificationError("recursive pair/authorization chain differs") from error
    if not isinstance(protected_trees,Mapping) or set(protected_trees)!={"a0","r1"} or protected_tree_verifier is None: raise A0XVerificationError("named a0/r1 protected-tree postflight checks required")
    verified_repository_root=repo.resolve(strict=True)
    for leg in ("a0","r1"):
        tree_manifest=protected_trees[leg]
        if not isinstance(tree_manifest,Mapping) or not isinstance(tree_manifest.get("protected_tree_sha256"),str): raise A0XVerificationError("protected-tree manifest invalid")
        if leg==leg_freeze.leg.value and tree_manifest["protected_tree_sha256"]!=leg_freeze.protected_tree_sha256: raise A0XVerificationError("relevant protected-tree manifest differs from frozen hash")
        try: protected_tree_verifier(verified_repository_root,tree_manifest,phase="postflight")
        except Exception as error: raise A0XVerificationError("protected-tree postflight verification failed") from error
    _report(raws.get("report",b""), values["terminal_result"]); _forbidden([manifest,root,*values.values()])

def verify_a0x_campaign_separation(manifests:Sequence[Mapping[str,Any]])->None:
    seen:set[tuple[str,str,str]]=set()
    for manifest in manifests:
        _forbidden([manifest]); pair=_pair(manifest); key=(pair.leg.value,pair.model_key,pair.revision)
        if key in seen: raise A0XVerificationError("duplicate frozen leg/model/revision")
        seen.add(key)

def _membership(pkg:Path,ledgers:Mapping[str,Sequence[Mapping[str,Any]]])->None:
    expected={"publication-manifest.json","output-occupancy-receipt.json"}; roles:set[str]=set()
    for e in ledgers["package_artifacts"]:
        if not isinstance(e.get("role"),str) or not isinstance(e.get("path"),str) or e["role"] in roles or e["path"] in expected: raise A0XVerificationError("duplicate package role/path")
        roles.add(e["role"]); expected.add(e["path"]); _safe(pkg,e["path"],e["role"])
    actual:set[str]=set()
    for p in pkg.rglob("*"):
        if p.is_dir() or p.is_symlink() or not p.is_file(): raise A0XVerificationError("undeclared directory/symlink/nonregular member")
        _regular(p,"package member"); actual.add(p.relative_to(pkg).as_posix())
    if actual!=expected: raise A0XVerificationError("package membership differs")

def _sources(repo:Path,ledger:Sequence[Mapping[str,Any]],dossier_path:str|Path,dossier_raw:bytes,auth_path:str|Path,auth_raw:bytes,raws:Mapping[str,bytes],seen:set[tuple[str,int,int]])->None:
    if {e["role"] for e in ledger}!={"dossier","authorization"}: raise A0XVerificationError("source ledger is not exact")
    expected={"dossier":(Path(dossier_path),dossier_raw),"authorization":(Path(auth_path),auth_raw)}
    for e in ledger:
        p,raw=expected[e["role"]]; p=_safe_repo(repo,p,e["role"]); _unique(p,seen,e["role"])
        if _repo_relative(repo,p,e["role"])!=e["repository_relative_path"] or len(raw)!=e["bytes"] or _sha(raw)!=e["raw_sha256"]: raise A0XVerificationError("source ledger differs")
    if raws.get("authorization_record")!=auth_raw: raise A0XVerificationError("authorization raw copy differs")

def _external(repo:Path,ledger:Sequence[Mapping[str,Any]],values:Mapping[str,Mapping[str,Any]],pair:PairBinding,seen:set[tuple[str,int,int]])->None:
    roles={e["role"] for e in ledger}; locator=values.get("external_assets_locator")
    if roles not in (set(),{"dense","index"}) or bool(roles)!=(locator is not None): raise A0XVerificationError("external matrix differs")
    if not roles:return
    if _pair(locator).as_mapping()!=pair.as_mapping() or locator.get("assets")!=list(ledger): raise A0XVerificationError("external locator differs")
    for e in ledger:
        p=_safe(repo,e["repository_relative_path"],e["role"]); _unique(p,seen,e["role"]); raw=_read(p,e["role"])
        if len(raw)!=e["bytes"] or _sha(raw)!=e["raw_sha256"]: raise A0XVerificationError("external raw differs")

def _residue(repo:Path,ledger:Sequence[Mapping[str,Any]],seen:set[tuple[str,int,int]])->None:
    roles:set[str]=set()
    for e in ledger:
        if e["role"] in roles: raise A0XVerificationError("duplicate residue role")
        roles.add(e["role"]); p=_safe(repo,e["repository_relative_path"],e["role"]); _unique(p,seen,e["role"]); raw=_read(p,e["role"])
        if len(raw)!=e["bytes"] or _sha(raw)!=e["raw_sha256"]: raise A0XVerificationError("residue raw differs")

def _matrix(manifest:Mapping[str,Any],a:Mapping[str,Mapping[str,Any]],raws:Mapping[str,bytes],freeze:LegFreezeBinding)->None:
    t=a.get("terminal_result"); roles=set(a); outputs={x["role"] for x in manifest["external_outputs"]}; residue=manifest["retained_residue"]; base={"authorization_record","terminal_result","report"}
    if t is None or t.get("status")!=manifest.get("terminal_status"): raise A0XVerificationError("terminal differs")
    state,status=t.get("sealed_from_state"),t.get("status")
    if state=="preflight":
        if status not in {"failed","incompatible"} or roles-base not in (set(),{"ccp_observation"}) or outputs: raise A0XVerificationError("preflight matrix differs")
    elif state=="activation":
        req=base|{"model_identity_receipt","ccp_observation","preflight_receipt"}; cond={"activation_receipt","external_assets_locator"}; has=cond.issubset(roles)
        if status not in {"failed","incompatible"} or not req.issubset(roles) or roles-(req|cond) or bool(roles&cond)!=has or bool(outputs)!=has or (has and outputs!={"dense","index"}): raise A0XVerificationError("activation matrix differs")
        if has: _activation_material(a["activation_receipt"],a["external_assets_locator"],freeze)
    elif state=="analysis":
        req=base|{"model_identity_receipt","ccp_observation","preflight_receipt","activation_receipt","target_read_receipt","external_assets_locator"}; want=req|({"statistical_result"} if status in {"positive","null"} else set())
        if status not in {"positive","null","non_interpretable","failed","incompatible"} or roles!=want or outputs!={"dense","index"} or (status in {"positive","null","non_interpretable"} and residue): raise A0XVerificationError("analysis matrix differs")
        target=a["target_read_receipt"]; activation=a["activation_receipt"]
        if t.get("analysis_target_content_reads")!=target.get("content_reads") or t.get("target_read_receipt_sha256")!=_sha(raws["target_read_receipt"]): raise A0XVerificationError("terminal/read counter differs")
        if status in {"positive","null","non_interpretable"} and (target.get("status")!="pass" or target.get("content_reads")!=1): raise A0XVerificationError("completed read differs")
        if target.get("selection_corpus_sha256")!=freeze.selection_corpus_sha256 or target.get("activation_receipt_sha256")!=_sha(raws["activation_receipt"]): raise A0XVerificationError("frozen target prerequisites differ")
        loc={x["role"]:x for x in a["external_assets_locator"]["assets"]}
        if target.get("dense_sha256")!=loc["dense"]["raw_sha256"] or target.get("index_sha256")!=loc["index"]["raw_sha256"]: raise A0XVerificationError("target asset hashes differ")
        _activation_material(activation,a["external_assets_locator"],freeze)
        if status in {"positive","null"} and t.get("statistical_result")!=a.get("statistical_result"): raise A0XVerificationError("statistical result differs")
    else: raise A0XVerificationError("unknown terminal frontier")

def _root(root:Mapping[str,Any],root_raw:bytes,manifest_raw:bytes,l:Mapping[str,Sequence[Mapping[str,Any]]],pair:PairBinding)->None:
    sums={"manifest":len(manifest_raw),"package_artifacts":sum(e["bytes"] for e in l["package_artifacts"]),"external_outputs":sum(e["bytes"] for e in l["external_outputs"]),"source_inputs":sum(e["bytes"] for e in l["source_inputs"]),"retained_residue":sum(e["bytes"] for e in l["retained_residue"])}; final=sums["manifest"]+sums["package_artifacts"]+sums["external_outputs"]+sums["retained_residue"]; checks=root.get("runtime_checkpoints")
    if root.get("manifest_raw_sha256")!=_sha(manifest_raw) or root.get("component_bytes")!=sums or root.get("final_bytes_excluding_this_receipt")!=final or root.get("cap_bytes")!=pair.dense_bound.cap_bytes or not isinstance(checks,list) or {x.get("phase") for x in checks}!={"pre_manifest_write","pre_root_receipt_write"}: raise A0XVerificationError("root arithmetic differs")
    peak=max(x["bytes"] for x in checks)
    if peak!=root.get("peak_bytes_before_this_receipt") or peak<final or max(peak,final+len(root_raw))>pair.dense_bound.cap_bytes: raise A0XVerificationError("root cap/checkpoints differ")
    activation=next((e for e in l["package_artifacts"] if e["role"]=="activation_receipt"),None)
    if root.get("activation_receipt_raw_sha256")!=(None if activation is None else activation["raw_sha256"]): raise A0XVerificationError("root activation hash differs")

def _activation_material(activation:Mapping[str,Any],locator:Mapping[str,Any],freeze:LegFreezeBinding)->None:
    assets={x["role"]:x for x in locator["assets"]}; dense=activation.get("dense"); index=activation.get("index"); occ=activation.get("activation_stage_occupancy")
    if not isinstance(dense,Mapping) or not isinstance(index,Mapping) or not isinstance(occ,Mapping): raise A0XVerificationError("activation material absent")
    for role,receipt in (("dense",dense),("index",index)):
        entry=assets.get(role)
        if not isinstance(entry,Mapping) or receipt.get("sha256")!=entry.get("raw_sha256") or receipt.get("bytes")!=entry.get("bytes") or Path(str(receipt.get("path",""))).name!=Path(str(entry.get("repository_relative_path",""))).name: raise A0XVerificationError("activation external path/size/hash differs")
    canon=(json.dumps(occ,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
    if activation.get("activation_status")!="completed" or activation.get("activation_target_content_reads")!=0 or activation.get("planned_dense_bound")!=activation["pair_binding"]["dense_bound"] or activation.get("activation_stage_occupancy_sha256")!=_sha(canon) or occ.get("leg")!=freeze.leg.value or occ.get("cap_bytes")!=activation["pair_binding"]["dense_bound"]["cap_bytes"] or occ.get("actual_total_bytes")!=dense.get("bytes",-1)+index.get("bytes",-1) or occ.get("included_paths")!=[str(dense.get("path")),str(index.get("path"))]: raise A0XVerificationError("activation occupancy differs")

def _report(raw:bytes,terminal:Mapping[str,Any])->None:
    try:text=raw.decode("utf-8")
    except UnicodeDecodeError as e:raise A0XVerificationError("report not UTF-8") from e
    from .a0x_report import render_a0x_report
    if raw != render_a0x_report(terminal_result=terminal): raise A0XVerificationError("report is not the exact frozen rendering")
def _safe(root:Path,rel:str,label:str)->Path:
    p=Path(rel)
    if p.is_absolute() or not rel or rel!=p.as_posix() or any(x in {".","..",""} for x in p.parts):raise A0XVerificationError(f"{label} unsafe path")
    cur=root
    for x in p.parts:
        cur/=x
        if os.path.lexists(cur) and cur.is_symlink():raise A0XVerificationError(f"{label} symlink component")
    try:cur.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError,ValueError) as e:raise A0XVerificationError(f"{label} escapes root") from e
    return _regular(cur,label)
def _safe_repo(root:Path,p:Path,label:str)->Path:
    try:return _safe(root,p.absolute().relative_to(root.absolute()).as_posix(),label)
    except (OSError,ValueError) as e:raise A0XVerificationError(f"{label} escapes repo") from e
def _safe_dir(root:Path,rel:str,label:str)->Path:
    p=Path(rel)
    if p.is_absolute() or not rel or rel.rstrip("/")!=p.as_posix() or any(x in {".","..",""} for x in p.parts): raise A0XVerificationError(f"{label} unsafe path")
    cur=root
    for x in p.parts:
        cur/=x
        if os.path.lexists(cur) and cur.is_symlink(): raise A0XVerificationError(f"{label} symlink component")
    try: cur.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError,ValueError) as e: raise A0XVerificationError(f"{label} escapes root") from e
    return _directory(cur,label)
def _directory(p:Path,label:str)->Path:
    if not p.is_dir() or p.is_symlink():raise A0XVerificationError(f"{label} unavailable")
    return p
def _regular(p:Path,label:str)->Path:
    try:s=p.lstat()
    except OSError as e:raise A0XVerificationError(f"{label} unavailable") from e
    if p.is_symlink() or not p.is_file() or s.st_nlink!=1:raise A0XVerificationError(f"{label} not unique regular")
    return p
def _read(p:Path,label:str)->bytes:return _regular(p,label).read_bytes()
def _unique(p:Path,seen:set[tuple[str,int,int]],label:str)->None:
    p=_regular(p,label).resolve(strict=True);s=p.stat(); key=(str(p),s.st_dev,s.st_ino)
    if key in seen:raise A0XVerificationError("physical alias forbidden")
    seen.add(key)
def _repo_relative(root:Path,p:Path,label:str)->str:return _safe_repo(root,p,label).relative_to(root).as_posix()
def _parse(raw:bytes,label:str,strict:bool=False)->dict[str,Any]:
    try:
        if raw.startswith(b"\xef\xbb\xbf"):raise ValueError("BOM")
        def pairs(x:list[tuple[str,Any]])->dict[str,Any]:
            out={}
            for k,v in x:
                if k in out:raise ValueError("duplicate")
                out[k]=v
            return out
        val=json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,parse_float=(lambda x: (_ for _ in ()).throw(ValueError("float"))) if strict else float,parse_constant=lambda x: (_ for _ in ()).throw(ValueError("non-finite")))
    except (UnicodeDecodeError,json.JSONDecodeError,ValueError) as e:raise A0XVerificationError(f"{label} invalid strict JSON") from e
    if not isinstance(val,dict):raise A0XVerificationError(f"{label} non-object")
    return val
def _json(p:Path,label:str,strict:bool=False)->tuple[bytes,dict[str,Any]]:
    raw=_read(p,label);return raw,_parse(raw,label,strict)
def _validate(v:Mapping[str,Any],schema:str,label:str)->None:
    try:s=json.loads((_ROOT/"schemas"/schema).read_text())
    except (OSError,json.JSONDecodeError) as e:raise A0XVerificationError(f"{label} schema unavailable") from e
    issues=validate(dict(v),s)
    if issues:raise A0XVerificationError(f"{label} schema rejected: {issues[0].message}")
def _pair(v:Mapping[str,Any])->PairBinding:
    try:return PairBinding.from_mapping(v["pair_binding"])
    except Exception as e:raise A0XVerificationError("invalid pair") from e
def _sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def _forbidden(values:Sequence[Any])->None:
    def walk(v:Any)->None:
        if isinstance(v,Mapping):
            for k,x in v.items():
                if k in {"aggregate","ranking","combined_p"}:raise A0XVerificationError("pooling field")
                walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
        elif isinstance(v,str) and ("exp002" in v.lower() or "exp-002" in v.lower() or "r5" in v.lower()):raise A0XVerificationError("excluded campaign")
    for v in values:walk(v)
__all__=["A0XVerificationError","verify_a0x_campaign_separation","verify_a0x_package"]
