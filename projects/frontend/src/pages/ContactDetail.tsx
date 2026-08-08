import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Mail, Phone, Linkedin, ExternalLink, MessageCircle } from 'lucide-react';
import { contactsApi } from '../api/client';
import type { Contact } from '../types';

export default function ContactDetail() {
  const { id } = useParams<{ id: string }>();
  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    contactsApi.get(id).then(setContact).catch(console.error).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="animate-pulse space-y-4"><div className="h-8 w-64 bg-slate-200 rounded" /><div className="h-64 bg-white rounded-xl border" /></div>;
  if (!contact) return <div className="text-center py-12 text-slate-500">Contact not found</div>;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link to={`/customers/${contact.company_id}`} className="p-2 rounded-lg hover:bg-slate-100 text-slate-400"><ArrowLeft size={20} /></Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{contact.full_name || 'Unknown Contact'}</h1>
          <p className="text-slate-500">{contact.job_title} at {contact.company_name}</p>
        </div>
        {contact.contact_grade && <ContactGradeBadge grade={contact.contact_grade} />}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
        {/* Role */}
        <div>
          <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Decision Role</h3>
          <p className="text-slate-900">{contact.decision_role || 'Not specified'}</p>
        </div>

        {/* Email */}
        <div>
          <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Email</h3>
          <div className="space-y-2">
            {contact.personal_email && (
              <div className="flex items-center gap-2">
                <Mail size={14} className="text-slate-400" />
                <a href={`mailto:${contact.personal_email}`} className="text-brand-600 hover:underline">{contact.personal_email}</a>
                {contact.email_status && <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-xs">{contact.email_status}</span>}
              </div>
            )}
            {contact.company_email && (
              <div className="flex items-center gap-2">
                <Mail size={14} className="text-slate-400" />
                <a href={`mailto:${contact.company_email}`} className="text-brand-600 hover:underline">{contact.company_email}</a>
                <span className="text-xs text-slate-400">(company)</span>
              </div>
            )}
            {!contact.personal_email && !contact.company_email && <p className="text-slate-400 text-sm">No email available</p>}
          </div>
        </div>

        {/* Phone */}
        <div>
          <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Phone</h3>
          <div className="space-y-2">
            {contact.personal_phone && (
              <div className="flex items-center gap-2">
                <Phone size={14} className="text-slate-400" />
                <span className="text-slate-900">{contact.personal_phone}</span>
                <a href={`https://wa.me/${contact.personal_phone.replace('+', '')}`} target="_blank" rel="noopener" className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs flex items-center gap-1 hover:bg-green-200">
                  <MessageCircle size={10} /> WhatsApp
                </a>
              </div>
            )}
            {contact.company_phone && (
              <div className="flex items-center gap-2">
                <Phone size={14} className="text-slate-400" />
                <span className="text-slate-900">{contact.company_phone}</span>
                <span className="text-xs text-slate-400">(company)</span>
              </div>
            )}
            {!contact.personal_phone && !contact.company_phone && <p className="text-slate-400 text-sm">No phone available</p>}
          </div>
        </div>

        {/* LinkedIn */}
        <div>
          <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">LinkedIn</h3>
          <div className="space-y-2">
            {contact.linkedin_personal && (
              <a href={contact.linkedin_personal} target="_blank" rel="noopener" className="flex items-center gap-2 text-blue-600 hover:underline">
                <Linkedin size={14} /> Personal Profile <ExternalLink size={10} />
              </a>
            )}
            {contact.linkedin_company && (
              <a href={contact.linkedin_company} target="_blank" rel="noopener" className="flex items-center gap-2 text-blue-600 hover:underline">
                <Linkedin size={14} /> Company Page <ExternalLink size={10} />
              </a>
            )}
            {!contact.linkedin_personal && !contact.linkedin_company && <p className="text-slate-400 text-sm">No LinkedIn available</p>}
          </div>
        </div>

        {/* Sources */}
        <div>
          <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Sources</h3>
          <div className="space-y-2 text-sm">
            {contact.identity_source_url && (
              <a href={contact.identity_source_url} target="_blank" rel="noopener" className="flex items-center gap-1.5 text-brand-600 hover:underline">
                <ExternalLink size={12} /> Identity Source
              </a>
            )}
            {contact.contact_source_url && (
              <a href={contact.contact_source_url} target="_blank" rel="noopener" className="flex items-center gap-1.5 text-brand-600 hover:underline">
                <ExternalLink size={12} /> Contact Info Source
              </a>
            )}
            <p className="text-slate-400 text-xs mt-2">Collected: {new Date(contact.collected_at).toLocaleDateString()}</p>
          </div>
        </div>

        {/* Notes */}
        {contact.research_notes && (
          <div>
            <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Research Notes</h3>
            <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3">{contact.research_notes}</p>
          </div>
        )}

        {/* Suggested Channel */}
        <div>
          <h3 className="text-xs font-medium text-slate-400 uppercase mb-2">Suggested Channel</h3>
          <span className="px-3 py-1 bg-brand-50 text-brand-700 rounded-lg text-sm font-medium">{contact.suggested_channel || 'Not determined'}</span>
        </div>
      </div>
    </div>
  );
}

function ContactGradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = { GOLD: 'bg-yellow-100 text-yellow-700 border-yellow-200', SILVER: 'bg-slate-100 text-slate-600 border-slate-200', BRONZE: 'bg-orange-100 text-orange-700 border-orange-200' };
  return <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${colors[grade] || ''}`}>{grade}</span>;
}
