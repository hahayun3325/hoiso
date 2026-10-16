# Historical Hunyuan CPU-load diagnostic source checkpoint

Attempt P8m5Dv2M stopped before submission with pinned_busctl_changed. Preserve these bytes as the used-attempt source; do not run review_driver.py, native_service.py, native_worker.py, or reuse the old attempt paths. Plans contain historical authorizations and bindings, not authorization to execute again.

This source snapshot is not yet integrated into the production pipeline. Actual CPU construction, checkpoint loading, inference and full parent acceptance remain pending. Source/fixture tests had passed locally before P8; this publication performs syntax validation only. The test scripts use simulated APIs and write diagnostic test reports beside themselves, so use a disposable copy if investigating them.

The worker and parent use read_helpers, cgroup_readers, cgroup_admission, service_protocol, manager_observation, interpreter_review and probe_storage. Plans and small original configuration/schema references retain provenance. Prior ZIPs, model weights, caches and transport_bundle.json are retained outside Git. The huge self-extracting server wrapper is intentionally represented by its source modules and its checksum in the progress note.

Original source location: /home/fredcui/tracehoi-hunyuan-cpu-budget-probe-20261014-v1-P8m5Dv2M. See SOURCE_MANIFEST.json for exact original bindings and fixture provenance.
