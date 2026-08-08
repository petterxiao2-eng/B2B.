import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Globe, Users, Star, Clock, Trash2, Edit } from 'lucide-react';
import { projectsApi } from '../api/client';
import type { Project } from '../types';

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();

  const load = () => {
    projectsApi.list().then(r => setProjects(r.projects)).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this project and all associated data?')) return;
    await projectsApi.delete(id);
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
          <p className="text-slate-500 mt-1">Manage your customer development campaigns</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700"
        >
          <Plus size={16} /> New Project
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-48 bg-white rounded-xl border border-slate-200 animate-pulse" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <Globe size={48} className="mx-auto text-slate-300 mb-4" />
          <h3 className="text-lg font-medium text-slate-700">No projects yet</h3>
          <p className="text-slate-500 mt-1 mb-4">Create your first customer development project</p>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-brand-600 text-white rounded-lg text-sm">
            Create Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(p => (
            <div
              key={p.id}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:border-brand-300 hover:shadow-sm transition-all cursor-pointer group"
              onClick={() => navigate(`/projects/${p.id}`)}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-900 group-hover:text-brand-600">{p.name}</h3>
                  <p className="text-sm text-slate-500 mt-0.5">{p.product_name}</p>
                </div>
                <StatusBadge status={p.status} />
              </div>

              <div className="flex flex-wrap gap-1.5 mb-4">
                {(p.target_markets || []).slice(0, 4).map(m => (
                  <span key={m} className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs">{m}</span>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="flex items-center gap-2">
                  <Star size={14} className="text-emerald-500" />
                  <span className="text-sm text-slate-600"><strong className="text-slate-900">{p.a_grade_customers}</strong> A-grade</span>
                </div>
                <div className="flex items-center gap-2">
                  <Users size={14} className="text-blue-500" />
                  <span className="text-sm text-slate-600"><strong className="text-slate-900">{p.total_customers}</strong> total</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <Clock size={12} />
                  {p.last_run_at ? new Date(p.last_run_at).toLocaleDateString() : 'Never run'}
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
                  <button
                    onClick={() => navigate(`/projects/${p.id}`)}
                    className="p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600"
                  >
                    <Edit size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateProjectModal onClose={() => setShowCreate(false)} onCreated={load} />}
    </div>
  );
}

function CreateProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    name: '',
    product_name: '',
    product_name_en: '',
    target_markets: '',
    priority_customer_types: 'distributor,importer,wholesaler',
    delivery_mode: '',
    key_advantages: '',
    target_quantity: 100,
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await projectsApi.create({
        ...form,
        target_markets: form.target_markets.split(',').map(s => s.trim()).filter(Boolean),
        priority_customer_types: form.priority_customer_types.split(',').map(s => s.trim()).filter(Boolean),
      });
      onCreated();
      onClose();
    } catch (e) {
      alert('Failed to create project');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-bold text-slate-900">New Project</h2>
        </div>
        <div className="p-6 space-y-4">
          <Field label="Project Name" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} placeholder="e.g., Solar Panel EU Expansion" />
          <Field label="Product Name (CN)" value={form.product_name} onChange={v => setForm(f => ({ ...f, product_name: v }))} placeholder="e.g., 太阳能板" />
          <Field label="Product Name (EN)" value={form.product_name_en} onChange={v => setForm(f => ({ ...f, product_name_en: v }))} placeholder="e.g., Solar Panel" />
          <Field label="Target Markets (comma-separated)" value={form.target_markets} onChange={v => setForm(f => ({ ...f, target_markets: v }))} placeholder="US, DE, UK, FR" />
          <Field label="Customer Types (comma-separated)" value={form.priority_customer_types} onChange={v => setForm(f => ({ ...f, priority_customer_types: v }))} placeholder="distributor, importer, wholesaler" />
          <Field label="Delivery Mode" value={form.delivery_mode} onChange={v => setForm(f => ({ ...f, delivery_mode: v }))} placeholder="FOB / CIF / DDP" />
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Key Advantages</label>
            <textarea
              value={form.key_advantages}
              onChange={e => setForm(f => ({ ...f, key_advantages: e.target.value }))}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              rows={3}
              placeholder="Describe your competitive advantages..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Target Quantity</label>
            <input
              type="number"
              value={form.target_quantity}
              onChange={e => setForm(f => ({ ...f, target_quantity: parseInt(e.target.value) || 100 }))}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>
        <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={saving || !form.name || !form.product_name}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
      />
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700',
    draft: 'bg-slate-100 text-slate-600',
    paused: 'bg-amber-100 text-amber-700',
    completed: 'bg-blue-100 text-blue-700',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status] || colors.draft}`}>
      {status}
    </span>
  );
}
