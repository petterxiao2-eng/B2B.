import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Play, Settings, Users, Star, Download, RefreshCw } from 'lucide-react';
import { projectsApi, companiesApi, tasksApi } from '../api/client';
import type { Project, Company } from '../types';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [customers, setCustomers] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    if (!id) return;
    Promise.all([
      projectsApi.get(id),
      companiesApi.list({ project_id: id, page: 1, page_size: 20 }),
    ]).then(([p, c]) => {
      setProject(p);
      setCustomers(c.companies);
    }).catch(console.error).finally(() => setLoading(false));
  }, [id]);

  const handleRunSearch = async () => {
    if (!id) return;
    try {
      await tasksApi.triggerSearch(id);
      alert('Search task created! Check Task Queue for progress.');
    } catch (e) {
      alert('Failed to trigger search');
    }
  };

  const handleBatchScore = async () => {
    if (!id) return;
    try {
      const result = await companiesApi.batchScore(id);
      alert(result.message);
      // Reload
      const c = await companiesApi.list({ project_id: id, page: 1, page_size: 20 });
      setCustomers(c.companies);
    } catch (e) {
      alert('Failed to score');
    }
  };

  if (loading) return <div className="animate-pulse space-y-4"><div className="h-8 w-64 bg-slate-200 rounded" /><div className="h-64 bg-white rounded-xl border border-slate-200" /></div>;
  if (!project) return <div className="text-center py-12 text-slate-500">Project not found</div>;

  const filtered = filter
    ? customers.filter(c => !filter || c.grade === filter)
    : customers;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/projects" className="p-2 rounded-lg hover:bg-slate-100 text-slate-400">
          <ArrowLeft size={20} />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-900">{project.name}</h1>
          <p className="text-slate-500">{project.product_name} {project.product_name_en && `(${project.product_name_en})`}</p>
        </div>
      </div>

      {/* Project Info */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Configuration</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Markets</dt><dd className="text-slate-900">{(project.target_markets || []).join(', ') || '-'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Customer Types</dt><dd className="text-slate-900">{(project.priority_customer_types || []).join(', ') || '-'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Delivery</dt><dd className="text-slate-900">{project.delivery_mode || '-'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Target</dt><dd className="text-slate-900">{project.target_quantity} companies</dd></div>
            </dl>
          </div>
          <div>
            <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Progress</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Total Customers</dt><dd className="font-medium text-slate-900">{project.total_customers}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">A-Grade</dt><dd className="font-medium text-emerald-600">{project.a_grade_customers}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Status</dt><dd><span className={`px-2 py-0.5 rounded text-xs font-medium ${project.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{project.status}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Last Run</dt><dd className="text-slate-900">{project.last_run_at ? new Date(project.last_run_at).toLocaleString() : 'Never'}</dd></div>
            </dl>
          </div>
          <div>
            <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Actions</h3>
            <div className="space-y-2">
              <button onClick={handleRunSearch} className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700">
                <Play size={14} /> Run Search
              </button>
              <button onClick={handleBatchScore} className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white text-slate-700 border border-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50">
                <RefreshCw size={14} /> Batch Score
              </button>
              <button onClick={() => companiesApi.exportCSV(id!)} className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white text-slate-700 border border-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50">
                <Download size={14} /> Export CSV
              </button>
            </div>
          </div>
        </div>
        {project.key_advantages && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <h4 className="text-xs font-medium text-slate-400 uppercase mb-1">Key Advantages</h4>
            <p className="text-sm text-slate-600">{project.key_advantages}</p>
          </div>
        )}
      </div>

      {/* Customer List */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Customers</h3>
          <div className="flex gap-2">
            {['', 'A', 'B', 'C', 'D'].map(g => (
              <button
                key={g}
                onClick={() => setFilter(g)}
                className={`px-3 py-1 rounded text-xs font-medium ${filter === g ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                {g || 'All'}
              </button>
            ))}
          </div>
        </div>
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <Users size={32} className="mx-auto mb-2 opacity-50" />
            <p>No customers found. Run a search to discover companies.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Company</th>
                  <th className="px-4 py-3 text-left">Country</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Score</th>
                  <th className="px-4 py-3 text-left">Grade</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => window.location.href = `/customers/${c.id}`}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{c.company_name}</div>
                      <div className="text-xs text-slate-400 truncate max-w-[200px]">{c.website}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{c.country || '-'}</td>
                    <td className="px-4 py-3 text-slate-600">{c.customer_type || '-'}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${c.score >= 75 ? 'bg-emerald-500' : c.score >= 60 ? 'bg-blue-500' : c.score >= 45 ? 'bg-amber-500' : 'bg-slate-300'}`} style={{ width: `${c.score}%` }} />
                        </div>
                        <span className="text-xs font-medium text-slate-700">{c.score.toFixed(0)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <GradeBadge grade={c.grade} />
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${c.review_status === 'approved' ? 'bg-emerald-100 text-emerald-700' : c.review_status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>
                        {c.review_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function GradeBadge({ grade }: { grade?: string }) {
  if (!grade) return <span className="text-xs text-slate-400">-</span>;
  const colors: Record<string, string> = {
    A: 'bg-emerald-100 text-emerald-700',
    B: 'bg-blue-100 text-blue-700',
    C: 'bg-amber-100 text-amber-700',
    D: 'bg-slate-100 text-slate-600',
    excluded: 'bg-red-100 text-red-600',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[grade] || colors.D}`}>
      {grade === 'excluded' ? 'EXC' : grade}
    </span>
  );
}
