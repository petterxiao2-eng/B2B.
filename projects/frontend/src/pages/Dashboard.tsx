import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FolderKanban, Users, UserCircle, ListTodo, FileText,
  TrendingUp, AlertCircle, CheckCircle2, Clock
} from 'lucide-react';
import { dashboardApi } from '../api/client';
import type { DashboardStats } from '../types';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      dashboardApi.getStats(),
      dashboardApi.getRecentActivity(),
    ]).then(([s, a]) => {
      setStats(s);
      setActivities(a.activities || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton />;
  if (!stats) return <div className="text-center py-12 text-slate-500">Failed to load dashboard</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1">Cross-border B2B customer growth overview</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FolderKanban}
          label="Active Projects"
          value={stats.projects.active}
          sub={`${stats.projects.total} total`}
          color="blue"
        />
        <StatCard
          icon={Users}
          label="Total Customers"
          value={stats.companies.total}
          sub={`${stats.companies.by_grade[0]?.count || 0} A-grade`}
          color="green"
        />
        <StatCard
          icon={UserCircle}
          label="Decision Makers"
          value={stats.contacts.total}
          sub={`${stats.contacts.gold} Gold contacts`}
          color="purple"
        />
        <StatCard
          icon={FileText}
          label="Pending Drafts"
          value={stats.drafts.pending_review}
          sub={`${stats.tasks.pending} tasks queued`}
          color="amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Grade Distribution */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Customer Grade Distribution</h3>
          <div className="space-y-3">
            {stats.companies.by_grade.map((g) => (
              <div key={g.grade} className="flex items-center gap-3">
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold text-white ${
                  g.grade === 'A' ? 'bg-emerald-500' :
                  g.grade === 'B' ? 'bg-blue-500' :
                  g.grade === 'C' ? 'bg-amber-500' : 'bg-slate-400'
                }`}>{g.grade}</span>
                <div className="flex-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">{g.label}</span>
                    <span className="font-medium text-slate-900">{g.count}</span>
                  </div>
                  <div className="mt-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        g.grade === 'A' ? 'bg-emerald-500' :
                        g.grade === 'B' ? 'bg-blue-500' :
                        g.grade === 'C' ? 'bg-amber-500' : 'bg-slate-400'
                      }`}
                      style={{ width: `${stats.companies.total ? (g.count / stats.companies.total) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Countries */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Top Countries</h3>
          <div className="space-y-2">
            {stats.companies.by_country.length === 0 ? (
              <p className="text-sm text-slate-400">No data yet</p>
            ) : (
              stats.companies.by_country.slice(0, 8).map((c, i) => (
                <div key={c.country} className="flex items-center justify-between py-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400 w-5">{i + 1}</span>
                    <span className="text-sm text-slate-700">{c.country}</span>
                  </div>
                  <span className="text-sm font-medium text-slate-900">{c.count}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Contact Quality */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Contact Quality</h3>
          <div className="space-y-4">
            <QualityBar label="GOLD" count={stats.contacts.gold} total={stats.contacts.total} color="bg-yellow-500" />
            <QualityBar label="SILVER" count={stats.contacts.silver} total={stats.contacts.total} color="bg-slate-400" />
            <QualityBar label="BRONZE" count={stats.contacts.bronze} total={stats.contacts.total} color="bg-orange-400" />
          </div>
          <div className="mt-6 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2 text-sm">
              <ListTodo size={16} className="text-slate-400" />
              <span className="text-slate-600">Tasks: {stats.tasks.running} running, {stats.tasks.pending} pending</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-700 mb-4">Recent Activity</h3>
        {activities.length === 0 ? (
          <p className="text-sm text-slate-400 py-4">No recent activity. Create a project to get started.</p>
        ) : (
          <div className="space-y-3">
            {activities.map((a, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                {a.type === 'company_discovered' ? (
                  <CheckCircle2 size={16} className="text-emerald-500 mt-0.5 shrink-0" />
                ) : (
                  <Clock size={16} className="text-blue-500 mt-0.5 shrink-0" />
                )}
                <div className="flex-1">
                  <p className="text-slate-700">{a.message}</p>
                  {a.timestamp && (
                    <p className="text-xs text-slate-400 mt-0.5">
                      {new Date(a.timestamp).toLocaleString()}
                    </p>
                  )}
                </div>
                {a.grade && <GradeBadge grade={a.grade} />}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Link to="/projects" className="inline-flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors">
          <FolderKanban size={16} /> Manage Projects
        </Link>
        <Link to="/customers" className="inline-flex items-center gap-2 px-4 py-2.5 bg-white text-slate-700 border border-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
          <Users size={16} /> View Customers
        </Link>
        <Link to="/drafts" className="inline-flex items-center gap-2 px-4 py-2.5 bg-white text-slate-700 border border-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
          <FileText size={16} /> Review Drafts
        </Link>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: any; label: string; value: number; sub: string; color: string;
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon size={20} />
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
          <p className="text-xs text-slate-500">{label}</p>
        </div>
      </div>
      <p className="text-xs text-slate-400 mt-2">{sub}</p>
    </div>
  );
}

function QualityBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total ? (count / total) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-900">{count}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function GradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = {
    A: 'bg-emerald-100 text-emerald-700',
    B: 'bg-blue-100 text-blue-700',
    C: 'bg-amber-100 text-amber-700',
    D: 'bg-slate-100 text-slate-600',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[grade] || 'bg-slate-100 text-slate-500'}`}>
      {grade}
    </span>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-slate-200 rounded" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-24 bg-white rounded-xl border border-slate-200" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-64 bg-white rounded-xl border border-slate-200" />
        ))}
      </div>
    </div>
  );
}
