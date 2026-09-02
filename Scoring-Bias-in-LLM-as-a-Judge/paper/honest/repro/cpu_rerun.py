#!/usr/bin/env python
"""CPU replication runner for scaled_harness.py.

Imports the harness unchanged (same ITEMS, PROBES, PERTURB, build_prompt,
score_logits) and overrides only what a CPU box needs:

  * families capped by MAX_B (default 3.0; 7-8B do not fit in 15GB RAM)
  * dtype: float32 up to FP32_MAX_B, bfloat16 above (3B in fp32 is 12GB)
  * OUT_PATH under the caller's control
  * resume: families already in OUT_PATH are skipped, so the run can be
    restarted after an interruption
  * SMOKE_ITEMS: score only the first N items (timing runs)

Usage:
  OUT_PATH=/path/out.json python cpu_rerun.py
  MAX_B=1.0 SMOKE_ITEMS=6 OUT_PATH=/tmp/smoke.json python cpu_rerun.py
"""
import os, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("R", "1")          # harness: skip its GPU pip-reinstall path
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
torch.set_num_threads(int(os.environ.get("THREADS", os.cpu_count() or 4)))
from transformers import AutoModelForCausalLM

import scaled_harness as H

OUT_PATH   = os.environ.get("OUT_PATH", os.path.join(HERE, "results_scaled_cpu_rerun.json"))
MAX_B      = float(os.environ.get("MAX_B", "3.0"))
FP32_MAX_B = float(os.environ.get("FP32_MAX_B", "2.0"))
SMOKE_ITEMS = int(os.environ.get("SMOKE_ITEMS", "0"))
ONLY = [s for s in os.environ.get("ONLY", "").split(",") if s]

if SMOKE_ITEMS:
    H.ITEMS = H.ITEMS[:SMOKE_ITEMS]

# Force the dtype chosen per family; the harness hardcodes float32 on CPU.
class _Loader:
    dtype = torch.float32
    @staticmethod
    def from_pretrained(name, **kw):
        kw["torch_dtype"] = _Loader.dtype
        kw.setdefault("low_cpu_mem_usage", True)
        return AutoModelForCausalLM.from_pretrained(name, **kw)
H.AutoModelForCausalLM = _Loader

def load_existing():
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            return json.load(f)
    return None

def main():
    import transformers
    pairs = [p for p in H.PAIRS if p[3] <= MAX_B and (not ONLY or p[0] in ONLY)]
    payload = load_existing() or {
        "env": {"torch": torch.__version__, "transformers": transformers.__version__,
                "device": H.DEVICE, "gpu": None,
                "cpu": open("/proc/cpuinfo").read().split("model name")[1].split("\n")[0].strip(": \t")
                       if os.path.exists("/proc/cpuinfo") else None,
                "threads": torch.get_num_threads(), "note": "CPU replication of results_scaled.json"},
        "smoke": bool(SMOKE_ITEMS), "n_items": len(H.ITEMS),
        "domains": [d for *_, d in H.ITEMS], "errors": {}, "results": {}, "timing_s": {}}
    print("ENV", payload["env"], flush=True)
    print("families:", [p[0] for p in pairs], "items:", len(H.ITEMS), flush=True)
    for label, base_id, inst_id, pb, train in pairs:
        if label in payload["results"] and "base" in payload["results"][label] \
                and "instruct" in payload["results"][label]:
            print(f"  {label}: already done, skipping", flush=True); continue
        _Loader.dtype = torch.float32 if pb <= FP32_MAX_B else torch.bfloat16
        rec = payload["results"].get(label, {"params_b": pb, "training": train})
        for kind, mid in (("base", base_id), ("instruct", inst_id)):
            if kind in rec:
                continue
            t0 = time.time()
            try:
                rec[kind] = H.score_one(mid)
                dt = time.time() - t0
                payload["timing_s"][f"{label}/{kind}"] = round(dt, 1)
                print(f"  {label}/{kind} ok ({dt:.0f}s, {str(_Loader.dtype).split('.')[-1]})", flush=True)
            except Exception as e:
                payload["errors"][mid] = f"{type(e).__name__}: {e}"
                print(f"  FAILED {mid}: {e}", flush=True)
            H.purge_cache()
            payload["results"][label] = rec
            with open(OUT_PATH, "w") as f:
                json.dump(payload, f, indent=2)
    print("\nWROTE", OUT_PATH, "families:", list(payload["results"].keys()), flush=True)

if __name__ == "__main__":
    main()
