# Work in progress: CPU replication of results_scaled.json

`results_scaled_cpu_rerun.partial.json` is a **checkpoint of a run still in
progress**, produced by `../cpu_rerun.py` on a 4-core Xeon with 15GB RAM
(fp32 up to 0.5B, bfloat16 above; each checkpoint records its dtype). It is
committed only so the run survives container restarts and can resume. It is
not data of record and nothing in the paper reads it. When all 10 families up
to 3B are complete, the finished file moves to `../results_scaled_cpu_rerun.json`,
gets a README row, and this directory is removed.
