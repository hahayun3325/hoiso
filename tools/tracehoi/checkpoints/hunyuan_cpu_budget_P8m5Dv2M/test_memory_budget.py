from pathlib import Path
from unittest.mock import patch
import json, math, sys
import native_service as ns
from read_helpers import E, H

N = Path(__file__).resolve().parent
plan = json.loads((N / 'review_plan.json').read_bytes())
budget = json.loads((N / 'memory_budget.json').read_bytes())
checks = []

def ck(value, name):
    assert value, name
    checks.append(name)

ns.configure(plan)
gib = 1024 ** 3
cases = [
    ('recorded_n7', 28820393984, 'max', 0, None),
    ('host_exact', 24 * gib, 'max', 0, None),
    ('host_below', 24 * gib - 1024, 'max', 0, 'host_memory_headroom_24GiB'),
    ('ancestor_exact', 24 * gib, str(25 * gib), 5 * gib, None),
    ('ancestor_below', 24 * gib, str(25 * gib), 5 * gib + 1, 'ancestor_memory_headroom_20GiB'),
]
for name, available, limit, current, error in cases:
    calls = []
    raw_host = ('MemTotal: 99999999 kB\nMemAvailable: %d kB\n' % (available // 1024)).encode()
    def reader(path, cap, check, row):
        calls.append(path)
        raw = raw_host if path == '/proc/meminfo' else ((limit if path.endswith('memory.max') else str(current)) + '\n').encode()
        row.update(binding=H(raw), complete=True)
        return raw
    record = {}
    with patch.object(ns, 'file_bytes', reader):
        try:
            ns.memory_admission(lambda: None, record)
        except ValueError as exc:
            ck(error == str(exc), 'expected_refusal:' + name)
        else:
            ck(error is None and record['complete'] and not record['reservation'], 'admitted:' + name)
    ck(record['host_available_bytes'] == available, 'saved_available:' + name)
    ck(record['host']['text'].encode() == raw_host and H(raw_host) == record['host']['binding'], 'reparseable_receipt:' + name)
    if name == 'host_below':
        ck(calls == ['/proc/meminfo'], 'refuse_before_ancestor_reads')

spec = plan['worker_plan']['cpu_load']
prior_half = 0
estimates = []
for row in budget['group_estimates']:
    prefix = row['group'] + '.'
    shapes = [shape for key, shape in spec['expected_schema'].items() if key.startswith(prefix)]
    half = 2 * sum(math.prod(shape) for shape in shapes)
    expected = spec['checkpoint_binding']['bytes'] + prior_half + 3 * half
    ck(row['current_group_f32_bytes'] == 2 * half and row['current_group_conversion_f16_bytes'] == half, 'schema_storage:' + row['group'])
    ck(row['retained_earlier_groups_f16_bytes'] == prior_half and row['estimated_tensor_storage_bytes'] == expected, 'group_estimate:' + row['group'])
    prior_half += half
    estimates.append(expected)
ck(max(estimates) == budget['known_tensor_storage_estimate_bytes'], 'estimate_from_schema')
ck(max(estimates) + budget['planning_native_overhead_bytes'] == budget['planning_estimate_with_overhead_bytes'] < budget['worker_memory_max_bytes'], 'planning_margin')
policy = {name: value for name, _, value in ns.wire.POLICY}
ck(policy['MemoryMax'] == budget['worker_memory_max_bytes'] == 20 * gib, 'worker_cap')
ck(policy['MemorySwapMax'] == budget['memory_swap_max_bytes'] == 0 and policy['TasksMax'] == budget['tasks_max'] == 32, 'swap_and_tasks')
ck(policy['RuntimeMaxUSec'] == budget['runtime_max_seconds'] * 1000000 == 300000000, 'runtime_cap')
ck(plan['memory_budget'] == budget and len(spec['expected_schema']) == 1645, 'plan_binding_and_tensor_count')
ck('torch' not in sys.modules and 'safetensors' not in sys.modules, 'no_native_execution')
(N / ('memory_budget_tests_python%d%d.json' % sys.version_info[:2])).write_bytes(E(dict(passed=True, count=len(checks), checks=checks)))
print('MEMORY_BUDGET', len(checks))
