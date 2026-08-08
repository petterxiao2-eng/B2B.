import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Search, Filter, Download, Users } from 'lucide-react';
import { companiesApi, projectsApi } from '../api/client';
import type { Company, Project } from '../types';

export default function CustomerList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const grade = searchParams.get('grade') || '';
  const country = searchParams.get('country') || '';
  const search = searchParams.get('search') || '';
  const projectId = searchParams.get('project_id') || '';

  useEffect(() => {
    projectsApi.list().then(r => setProjects(r.projects)).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string | number | undefined> = { page, page_size: 20 };
    if (grade) params.grade = grade;
    if (country) params.country = country;
    if (search) params.search = search;
    if (projectId) params.project_id = projectId;

    companiesApi.list(params)
      .then(r => { setCompanies(r.companies); setTotal(r.total); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [grade, country, search, projectId, page]);

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value); else params.delete(key);
    setSearchParams(params);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Customers</h1>
          <p className="text-slate-500 mt-1">{total} companies discovered</p>
        </div>
        {projectId && (
          <button onClick={() => companiesApi.exportCSV(projectId, grade || undefined)} className="inline-flex items-center gap-2 px-4 py-2 bg-white text-slate-700 border border-slate-200 rounded-lg text-sm hover:bg-slate-50">
            <Download size={16} /> Export
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search companies..."
                value={search}
                onChange={e => updateFilter('search', e.target.value)}
                className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
          <select value={projectId} onChange={e => updateFilter('project_id', e.target.value)} className="px-3 py-2 border border-slate-200 rounded-lg text-sm">
            <option value="">All Projects</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select value={grade} onChange={e => updateFilter('grade', e.target.value)} className="px-3 py-2 border border-slate-200 rounded-lg text-sm">
            <option value="">All Grades</option>
            <option value="A">A - Priority</option>
            <option value="B">B - Developable</option>
            <option value="C">C - Watch</option>
            <option value="D">D - Low Priority</option>
          </select>
          <button
            onClick={() => {
              const params = new URLSearchParams();
              if (projectId) params.set('project_id', projectId);
              if (grade) params.set('grade', grade);
              if (country) params.set('country', country);
              if (search) params.set('search', search);
              window.location.href = `/api/companies/export/csv?${params.toString()}`;
            }}
            className="flex items-center gap-1.5 px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 transition-colors"
          >
            <Download size={14} />
            Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-400 animate-pulse">Loading...</div>
        ) : companies.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <Users size={32} className="mx-auto mb-2 opacity-50" />
            <p>No customers found</p>
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
                  <th className="px-4 py-3 text-left">WhatsApp</th>
                  <th className="px-4 py-3 text-left">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {companies.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => window.location.href = `/customers/${c.id}`}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{c.company_name}</div>
                      {c.website && <a href={c.website} target="_blank" rel="noopener" className="text-xs text-brand-600 hover:underline" onClick={e => e.stopPropagation()}>{c.website.replace(/^https?:\/\/(www\.)?/, '').slice(0, 40)}</a>}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{c.country || '-'}</td>
                    <td className="px-4 py-3 text-slate-600">{c.customer_type || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`font-medium ${c.score >= 75 ? 'text-emerald-600' : c.score >= 60 ? 'text-blue-600' : 'text-slate-600'}`}>{c.score.toFixed(0)}</span>
                    </td>
                    <td className="px-4 py-3"><GradeBadge grade={c.grade} /></td>
                    <td className="px-4 py-3">
                      {c.whatsapp_numbers && c.whatsapp_numbers.length > 0 ? (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">{c.whatsapp_numbers.length} number(s)</span>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 max-w-[150px] truncate">{c.discovery_path || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > 20 && (
          <div className="p-4 border-t border-slate-200 flex items-center justify-between">
            <span className="text-sm text-slate-500">Page {page} of {Math.ceil(total / 20)}</span>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border border-slate-200 rounded text-sm disabled:opacity-50">Prev</button>
              <button disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border border-slate-200 rounded text-sm disabled:opacity-50">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function GradeBadge({ grade }: { grade?: string }) {
  if (!grade) return <span className="text-xs text-slate-400">-</span>;
  const colors: Record<string, string> = { A: 'bg-emerald-100 text-emerald-700', B: 'bg-blue-100 text-blue-700', C: 'bg-amber-100 text-amber-700', D: 'bg-slate-100 text-slate-600', excluded: 'bg-red-100 text-red-600' };
  return <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[grade] || colors.D}`}>{grade === 'excluded' ? 'EXC' : grade}</span>;
}
