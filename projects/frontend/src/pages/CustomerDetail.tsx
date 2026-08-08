import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink, MessageCircle, Mail, Linkedin, Phone, Star, MapPin, Globe, Search, UserSearch, RefreshCw, Shield } from 'lucide-react';
import { companiesApi, draftsApi } from '../api/client';
import type { Company, Contact } from '../types';

export default function CustomerDetail() {
  const { id } = useParams<{ id: string }>();
  const [company, setCompany] = useState<Company | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadData = () => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      companiesApi.get(id),
      companiesApi.getContacts(id),
    ]).then(([c, ct]) => {
      setCompany(c);
      setContacts(ct.contacts);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [id]);

  const handleGenerateDraft = async (channel: string) => {
    if (!id) return;
    try {
      await draftsApi.generate(id, undefined, channel);
      alert(`Draft generated! Check Draft Review page.`);
    } catch (e) {
      alert('Failed to generate draft');
    }
  };

  const handleBackgroundCheck = async () => {
    if (!id) return;
    setActionLoading('background');
    try {
      await companiesApi.backgroundCheck(id);
      await loadData();
      alert('Background check completed!');
    } catch (e: unknown) {
      alert(`Background check failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleResearchContacts = async () => {
    if (!id) return;
    setActionLoading('contacts');
    try {
      const result = await companiesApi.researchContacts(id);
      await loadData();
      alert(`Contact research completed! Found ${result.contacts_found} contacts.`);
    } catch (e: unknown) {
      alert(`Contact research failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return <div className="animate-pulse space-y-4"><div className="h-8 w-64 bg-slate-200 rounded" /><div className="h-96 bg-white rounded-xl border" /></div>;
  if (!company) return <div className="text-center py-12 text-slate-500">Company not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/customers" className="p-2 rounded-lg hover:bg-slate-100 text-slate-400"><ArrowLeft size={20} /></Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-900">{company.company_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            {company.website && <a href={company.website} target="_blank" rel="noopener" className="text-sm text-brand-600 hover:underline flex items-center gap-1"><Globe size={12} />{company.website}</a>}
            {company.country && <span className="text-sm text-slate-500 flex items-center gap-1"><MapPin size={12} />{company.city ? `${company.city}, ` : ''}{company.country}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={handleBackgroundCheck} disabled={actionLoading === 'background' || !company.website} className="px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1.5" title="Scrape & analyze company website">
            {actionLoading === 'background' ? <RefreshCw size={14} className="animate-spin" /> : <Shield size={14} />} Background Check
          </button>
          <button onClick={handleResearchContacts} disabled={actionLoading === 'contacts' || !['A', 'B'].includes(company.grade || '')} className="px-3 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50 flex items-center gap-1.5" title="Research decision makers (A/B grade only)">
            {actionLoading === 'contacts' ? <RefreshCw size={14} className="animate-spin" /> : <UserSearch size={14} />} Research Contacts
          </button>
          <button onClick={() => handleGenerateDraft('email')} className="px-3 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700 flex items-center gap-1.5"><Mail size={14} /> Email Draft</button>
          <button onClick={() => handleGenerateDraft('whatsapp')} className="px-3 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 flex items-center gap-1.5"><MessageCircle size={14} /> WhatsApp</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Score Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-900">Scoring Details</h3>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-slate-900">{company.score.toFixed(0)}</span>
                <GradeBadge grade={company.grade} />
              </div>
            </div>
            {company.score_details && (
              <div className="space-y-2">
                {Object.entries(company.score_details).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-sm text-slate-500 w-44 capitalize">{key.replace(/_/g, ' ')}</span>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${
                        key === 'product_match' ? 'bg-blue-500' :
                        key === 'customer_type_match' ? 'bg-purple-500' :
                        key === 'procurement_capability' ? 'bg-emerald-500' :
                        key === 'business_scale' ? 'bg-amber-500' :
                        key === 'market_value' ? 'bg-cyan-500' : 'bg-slate-400'
                      }`} style={{ width: `${(val as number) / (key === 'product_match' ? 25 : key === 'customer_type_match' || key === 'procurement_capability' ? 20 : key === 'business_scale' ? 15 : 10) * 100}%` }} />
                    </div>
                    <span className="text-sm font-medium text-slate-700 w-10 text-right">{val as number}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Business Profile */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-4">Business Profile</h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div><dt className="text-slate-400">Customer Type</dt><dd className="text-slate-900 mt-0.5">{company.customer_type || '-'}</dd></div>
              <div><dt className="text-slate-400">Main Business</dt><dd className="text-slate-900 mt-0.5">{company.main_business || '-'}</dd></div>
              <div><dt className="text-slate-400">Related Products</dt><dd className="text-slate-900 mt-0.5">{company.related_products || '-'}</dd></div>
              <div><dt className="text-slate-400">Discovery Path</dt><dd className="text-slate-900 mt-0.5">{company.discovery_path || '-'}</dd></div>
            </dl>
            {company.product_match_evidence && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <dt className="text-slate-400 text-sm">Product Match Evidence</dt>
                <dd className="text-slate-700 text-sm mt-1">{company.product_match_evidence}</dd>
              </div>
            )}
            {company.procurement_capability && (
              <div className="mt-3">
                <dt className="text-slate-400 text-sm">Procurement Capability</dt>
                <dd className="text-slate-700 text-sm mt-1">{company.procurement_capability}</dd>
              </div>
            )}
          </div>

          {/* Background Report */}
          {company.background_report && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900 flex items-center gap-2"><Shield size={16} className="text-indigo-500" /> Background Report</h3>
                {company.background_report.scraped_at && (
                  <span className="text-xs text-slate-400">Scraped: {new Date(company.background_report.scraped_at).toLocaleDateString()}</span>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                {company.background_report.founded_year && <div><dt className="text-slate-400">Founded</dt><dd className="text-slate-900">{company.background_report.founded_year}</dd></div>}
                {company.background_report.company_size && <div><dt className="text-slate-400">Company Size</dt><dd className="text-slate-900">{company.background_report.company_size}</dd></div>}
                {company.background_report.employee_count && <div><dt className="text-slate-400">Employees</dt><dd className="text-slate-900">{company.background_report.employee_count}</dd></div>}
                {company.background_report.revenue && <div><dt className="text-slate-400">Revenue</dt><dd className="text-slate-900">{company.background_report.revenue}</dd></div>}
                {company.background_report.main_markets?.length > 0 && <div className="md:col-span-2"><dt className="text-slate-400">Main Markets</dt><dd className="text-slate-900">{company.background_report.main_markets.join(', ')}</dd></div>}
                {company.background_report.business_scope && <div className="md:col-span-2"><dt className="text-slate-400">Business Scope</dt><dd className="text-slate-700 mt-0.5">{company.background_report.business_scope}</dd></div>}
              </div>
              {company.background_report.product_lines?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <dt className="text-slate-400 text-sm mb-2">Product Lines</dt>
                  <div className="flex flex-wrap gap-1.5">
                    {company.background_report.product_lines.map((p: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {company.background_report.branches?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <dt className="text-slate-400 text-sm mb-2">Branches / Locations</dt>
                  <ul className="text-sm text-slate-700 space-y-1">
                    {company.background_report.branches.map((b: string, i: number) => (
                      <li key={i} className="flex items-center gap-1.5"><MapPin size={12} className="text-slate-400" />{b}</li>
                    ))}
                  </ul>
                </div>
              )}
              {company.background_report.social_media && Object.keys(company.background_report.social_media).length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <dt className="text-slate-400 text-sm mb-2">Social Media</dt>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(company.background_report.social_media).map(([platform, url]) => (
                      <a key={platform} href={url as string} target="_blank" rel="noopener" className="px-2 py-1 bg-slate-50 rounded text-xs text-brand-600 hover:underline capitalize flex items-center gap-1">
                        <ExternalLink size={10} /> {platform}
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {company.background_report.industry_associations?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <dt className="text-slate-400 text-sm mb-2">Industry Associations</dt>
                  <ul className="text-sm text-slate-700 space-y-1">
                    {company.background_report.industry_associations.map((a: string, i: number) => (
                      <li key={i}>• {a}</li>
                    ))}
                  </ul>
                </div>
              )}
              {company.background_report.emails_found?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <dt className="text-slate-400 text-sm mb-2">Emails Found</dt>
                  <div className="flex flex-wrap gap-1.5">
                    {company.background_report.emails_found.map((e: string, i: number) => (
                      <a key={i} href={`mailto:${e}`} className="px-2 py-0.5 bg-slate-50 rounded text-xs text-brand-600 hover:underline flex items-center gap-1"><Mail size={10} />{e}</a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Contacts */}
          <div className="bg-white rounded-xl border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Decision Makers ({contacts.length})</h3>
            </div>
            {contacts.length === 0 ? (
              <div className="p-6 text-center text-slate-400 text-sm">No contacts found. Contacts are researched for A/B grade companies.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {contacts.map(c => (
                  <div key={c.id} className="p-4 hover:bg-slate-50 cursor-pointer" onClick={() => window.location.href = `/contacts/${c.id}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-900">{c.full_name || 'Unknown'}</span>
                          <ContactGradeBadge grade={c.contact_grade} />
                        </div>
                        <p className="text-sm text-slate-500">{c.job_title} {c.decision_role && `(${c.decision_role})`}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {c.personal_email && <Mail size={14} className="text-slate-400" />}
                        {c.linkedin_personal && <Linkedin size={14} className="text-blue-500" />}
                        {c.personal_phone && <Phone size={14} className="text-green-500" />}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Sources */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-3">Sources</h3>
            <div className="space-y-2 text-sm">
              {company.source_url_1 && <a href={company.source_url_1} target="_blank" rel="noopener" className="flex items-center gap-1.5 text-brand-600 hover:underline truncate"><ExternalLink size={12} />Source 1</a>}
              {company.source_url_2 && <a href={company.source_url_2} target="_blank" rel="noopener" className="flex items-center gap-1.5 text-brand-600 hover:underline truncate"><ExternalLink size={12} />Source 2</a>}
              <p className="text-slate-400 text-xs mt-2">Collected: {new Date(company.collected_at).toLocaleDateString()}</p>
            </div>
          </div>

          {/* WhatsApp */}
          {company.whatsapp_numbers && company.whatsapp_numbers.length > 0 && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-6">
              <h3 className="font-semibold text-green-800 mb-3 flex items-center gap-2"><MessageCircle size={16} /> WhatsApp</h3>
              <div className="space-y-2">
                {company.whatsapp_numbers.map((num, i) => (
                  <a key={i} href={`https://wa.me/${num.replace('+', '')}`} target="_blank" rel="noopener" className="flex items-center gap-2 text-green-700 hover:underline text-sm">
                    <Phone size={12} /> {num}
                  </a>
                ))}
              </div>
              {company.whatsapp_group_links?.map((link, i) => (
                <a key={i} href={link} target="_blank" rel="noopener" className="flex items-center gap-2 text-green-700 hover:underline text-sm mt-1">
                  <ExternalLink size={12} /> Group Link
                </a>
              ))}
            </div>
          )}

          {/* Customs Data */}
          {company.customs_data && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-900 mb-3">Customs Data</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between"><dt className="text-slate-500">Import Records</dt><dd className="font-medium">{company.customs_data.import_records || 0}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">Frequency</dt><dd>{company.customs_data.purchase_frequency || '-'}</dd></div>
              </dl>
            </div>
          )}

          {/* Review Status */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-3">Review</h3>
            <span className={`px-3 py-1 rounded-lg text-sm font-medium ${company.review_status === 'approved' ? 'bg-emerald-100 text-emerald-700' : company.review_status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
              {company.review_status}
            </span>
            {company.suggested_approach && (
              <div className="mt-3">
                <dt className="text-xs text-slate-400">Suggested Approach</dt>
                <dd className="text-sm text-slate-600 mt-1">{company.suggested_approach}</dd>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function GradeBadge({ grade }: { grade?: string }) {
  if (!grade) return null;
  const colors: Record<string, string> = { A: 'bg-emerald-100 text-emerald-700', B: 'bg-blue-100 text-blue-700', C: 'bg-amber-100 text-amber-700', D: 'bg-slate-100 text-slate-600' };
  return <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[grade] || ''}`}>{grade}</span>;
}

function ContactGradeBadge({ grade }: { grade?: string }) {
  if (!grade) return null;
  const colors: Record<string, string> = { GOLD: 'bg-yellow-100 text-yellow-700', SILVER: 'bg-slate-200 text-slate-600', BRONZE: 'bg-orange-100 text-orange-700' };
  return <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${colors[grade] || ''}`}>{grade}</span>;
}
