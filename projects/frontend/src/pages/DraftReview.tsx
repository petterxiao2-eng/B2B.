import { useEffect, useState } from 'react';
import { Mail, MessageCircle, Check, X, Edit2, Send, Eye } from 'lucide-react';
import { draftsApi } from '../api/client';
import type { DraftMessage } from '../types';

export default function DraftReview() {
  const [drafts, setDrafts] = useState<DraftMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState('');
  const [previewId, setPreviewId] = useState<string | null>(null);

  const load = () => {
    const params: Record<string, string | undefined> = {};
    if (filter) params.status = filter;
    draftsApi.list(params).then(r => setDrafts(r.drafts)).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(load, [filter]);

  const handleApprove = async (id: string) => {
    await draftsApi.update(id, { status: 'approved' });
    load();
  };

  const handleSend = async (id: string) => {
    if (!confirm('Mark this draft as sent?')) return;
    await draftsApi.update(id, { status: 'sent' });
    load();
  };

  const handleReject = async (id: string) => {
    await draftsApi.update(id, { status: 'rejected' });
    load();
  };

  const handleSaveEdit = async (id: string) => {
    await draftsApi.update(id, { body: editBody });
    setEditingId(null);
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Draft Review</h1>
          <p className="text-slate-500 mt-1">Review and approve personalized outreach drafts</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {[
          { value: '', label: 'All' },
          { value: 'draft', label: 'Drafts' },
          { value: 'approved', label: 'Approved' },
          { value: 'sent', label: 'Sent' },
          { value: 'rejected', label: 'Rejected' },
        ].map(f => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${filter === f.value ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Drafts List */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <div key={i} className="h-48 bg-white rounded-xl border border-slate-200 animate-pulse" />)}
        </div>
      ) : drafts.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <Mail size={48} className="mx-auto text-slate-300 mb-4" />
          <h3 className="text-lg font-medium text-slate-700">No drafts</h3>
          <p className="text-slate-500 mt-1">Generate drafts from customer detail pages</p>
        </div>
      ) : (
        <div className="space-y-4">
          {drafts.map(d => (
            <div key={d.id} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${d.channel === 'email' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'}`}>
                    {d.channel === 'email' ? <Mail size={16} /> : <MessageCircle size={16} />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900 capitalize">{d.channel}</span>
                      <DraftStatusBadge status={d.status} />
                    </div>
                    {d.subject && <p className="text-sm text-slate-500">{d.subject}</p>}
                    <p className="text-xs text-slate-400">{new Date(d.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => { setPreviewId(previewId === d.id ? null : d.id); }} className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600" title="Preview">
                    <Eye size={16} />
                  </button>
                  {d.status === 'draft' && (
                    <>
                      <button onClick={() => { setEditingId(d.id); setEditBody(d.body); }} className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600" title="Edit">
                        <Edit2 size={16} />
                      </button>
                      <button onClick={() => handleApprove(d.id)} className="p-2 rounded-lg hover:bg-emerald-50 text-slate-400 hover:text-emerald-600" title="Approve">
                        <Check size={16} />
                      </button>
                      <button onClick={() => handleReject(d.id)} className="p-2 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500" title="Reject">
                        <X size={16} />
                      </button>
                    </>
                  )}
                  {d.status === 'approved' && (
                    <button onClick={() => handleSend(d.id)} className="p-2 rounded-lg hover:bg-blue-50 text-slate-400 hover:text-blue-600" title="Mark as Sent">
                      <Send size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Content Breakdown */}
              {d.content_breakdown && (
                <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex flex-wrap gap-3 text-xs text-slate-500">
                  <span>Product: {d.content_breakdown.product_capability_pct || 70}%</span>
                  <span>Personalized: {d.content_breakdown.personalization_pct || 30}%</span>
                  {d.content_breakdown.cta && <span>CTA: {d.content_breakdown.cta}</span>}
                </div>
              )}

              {/* Edit Mode */}
              {editingId === d.id ? (
                <div className="p-4">
                  <textarea
                    value={editBody}
                    onChange={e => setEditBody(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:ring-2 focus:ring-brand-500"
                    rows={8}
                  />
                  <div className="flex justify-end gap-2 mt-2">
                    <button onClick={() => setEditingId(null)} className="px-3 py-1.5 text-sm text-slate-600">Cancel</button>
                    <button onClick={() => handleSaveEdit(d.id)} className="px-3 py-1.5 bg-brand-600 text-white rounded-lg text-sm">Save</button>
                  </div>
                </div>
              ) : previewId === d.id ? (
                <div className="p-4">
                  <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans bg-slate-50 rounded-lg p-4">{d.body}</pre>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DraftStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600',
    approved: 'bg-emerald-100 text-emerald-700',
    sent: 'bg-blue-100 text-blue-700',
    rejected: 'bg-red-100 text-red-700',
  };
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status] || colors.draft}`}>{status}</span>;
}
