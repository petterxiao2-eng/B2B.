import { useEffect, useState } from 'react';
import { Play, Pause, RefreshCw, AlertCircle, CheckCircle2, Clock, Loader2, Wifi, WifiOff, Globe, Server } from 'lucide-react';
import { tasksApi } from '../api/client';

export default function TaskQueue() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [scheduled, setScheduled] = useState<any[]>([]);
  const [proxyStatus, setProxyStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([
      tasksApi.list({}),
      tasksApi.getQueueStats(),
      tasksApi.getScheduled(),
      tasksApi.getProxyStatus(),
    ]).then(([t, s, j, p]) => {
      setTasks(t.tasks);
      setStats(s);
      setScheduled(j.jobs);
      setProxyStatus(p);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(load, []);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Task Queue</h1>
          <p className="text-slate-500 mt-1">Monitor search tasks, scheduled jobs and proxy pool</p>
        </div>
        <button onClick={load} className="inline-flex items-center gap-2 px-4 py-2 bg-white text-slate-700 border border-slate-200 rounded-lg text-sm hover:bg-slate-50">
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* Queue Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <QueueStat label="Pending" value={stats.by_status.pending || 0} icon={Clock} color="text-amber-500" bg="bg-amber-50" />
          <QueueStat label="Running" value={stats.by_status.running || 0} icon={Loader2} color="text-blue-500" bg="bg-blue-50" />
          <QueueStat label="Completed" value={stats.by_status.completed || 0} icon={CheckCircle2} color="text-emerald-500" bg="bg-emerald-50" />
          <QueueStat label="Failed" value={stats.by_status.failed || 0} icon={AlertCircle} color="text-red-500" bg="bg-red-50" />
        </div>
      )}

      {/* Task List */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">Recent Tasks</h3>
        </div>
        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading...</div>
        ) : tasks.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <Clock size={32} className="mx-auto mb-2 opacity-50" />
            <p>No tasks yet. Trigger a search from a project page.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Priority</th>
                  <th className="px-4 py-3 text-left">Created</th>
                  <th className="px-4 py-3 text-left">Started</th>
                  <th className="px-4 py-3 text-left">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tasks.map(t => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-medium">{t.task_type}</span>
                    </td>
                    <td className="px-4 py-3">
                      <TaskStatusBadge status={t.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-600">{t.priority}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{t.created_at ? new Date(t.created_at).toLocaleString() : '-'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{t.started_at ? new Date(t.started_at).toLocaleString() : '-'}</td>
                    <td className="px-4 py-3 text-red-500 text-xs max-w-[200px] truncate">{t.error_message || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Scheduled Jobs */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">Scheduled Jobs</h3>
        </div>
        {scheduled.length === 0 ? (
          <div className="p-6 text-center text-slate-400 text-sm">No scheduled jobs configured</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {scheduled.map(j => (
              <div key={j.id} className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-900">{j.job_type}</p>
                  <p className="text-sm text-slate-500">Every {j.interval_hours}h</p>
                </div>
                <div className="flex items-center gap-2">
                  {j.is_active ? (
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded text-xs">Active</span>
                  ) : (
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-xs">Inactive</span>
                  )}
                  {j.last_run_at && <span className="text-xs text-slate-400">Last: {new Date(j.last_run_at).toLocaleString()}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Proxy Pool Status */}
      {proxyStatus && (
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server size={18} className="text-slate-500" />
              <h3 className="font-semibold text-slate-900">Proxy Pool Status</h3>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-emerald-600 font-medium">{proxyStatus.summary.healthy} healthy</span>
              <span className="text-red-500">{proxyStatus.summary.degraded} degraded</span>
              <span className="text-slate-400">|</span>
              <span className="text-slate-500">Avg latency: {proxyStatus.summary.avg_latency_ms}ms</span>
            </div>
          </div>

          {/* Region Summary */}
          <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 border-b border-slate-100">
            {proxyStatus.by_region.map((r: any) => (
              <div key={r.region} className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">{r.region}</p>
                <p className="text-lg font-bold text-slate-900">{r.healthy}/{r.total}</p>
                <div className="w-full bg-slate-200 rounded-full h-1.5 mt-1">
                  <div
                    className={`h-1.5 rounded-full ${r.healthy === r.total ? 'bg-emerald-500' : r.healthy > r.total * 0.5 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${(r.healthy / r.total) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Proxy List */}
          <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">ID</th>
                  <th className="px-4 py-2 text-left">Region</th>
                  <th className="px-4 py-2 text-left">IP:Port</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Latency</th>
                  <th className="px-4 py-2 text-left">Success Rate</th>
                  <th className="px-4 py-2 text-left">Requests Today</th>
                  <th className="px-4 py-2 text-left">Last Check</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {proxyStatus.proxies.slice(0, 20).map((p: any) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2 text-xs font-mono text-slate-500">{p.id}</td>
                    <td className="px-4 py-2">
                      <span className="text-xs">{p.country} {p.region}</span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{p.ip}:{p.port}</td>
                    <td className="px-4 py-2">
                      {p.status === 'healthy' ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600"><Wifi size={10} /> Healthy</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-500"><WifiOff size={10} /> Degraded</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <span className={p.latency_ms < 500 ? 'text-emerald-600' : p.latency_ms < 2000 ? 'text-amber-600' : 'text-red-500'}>
                        {p.latency_ms}ms
                      </span>
                    </td>
                    <td className="px-4 py-2">{(p.success_rate * 100).toFixed(0)}%</td>
                    <td className="px-4 py-2 text-slate-500">{p.requests_today}</td>
                    <td className="px-4 py-2 text-xs text-slate-400">{new Date(p.last_check).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {proxyStatus.proxies.length > 20 && (
            <div className="p-3 text-center text-xs text-slate-400 border-t border-slate-100">
              Showing 20 of {proxyStatus.proxies.length} proxies
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function QueueStat({ label, value, icon: Icon, color, bg }: { label: string; value: number; icon: any; color: string; bg: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${bg} ${color}`}><Icon size={18} /></div>
      <div>
        <p className="text-xl font-bold text-slate-900">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}

function TaskStatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; icon: any }> = {
    pending: { color: 'bg-amber-100 text-amber-700', icon: Clock },
    running: { color: 'bg-blue-100 text-blue-700', icon: Loader2 },
    completed: { color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
    failed: { color: 'bg-red-100 text-red-700', icon: AlertCircle },
  };
  const c = config[status] || config.pending;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${c.color}`}>
      <c.icon size={10} /> {status}
    </span>
  );
}
