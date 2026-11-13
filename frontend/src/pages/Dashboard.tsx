import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Database,
  RefreshCw,
  Users,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { reportsApi, syncApi } from '../api/client';
import type { ReportData } from '../types';

interface DashboardProps {
  onSelectCourse: (courseId: number) => void;
  onNavigate: (tab: string) => void;
}

export function Dashboard({ onSelectCourse, onNavigate }: DashboardProps) {
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const data = await reportsApi.getReport('R18');
      setReport(data);
    } catch {
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const handleSeedDemo = async () => {
    setBusy(true);
    setMessage(null);
    try {
      await syncApi.seedDemo();
      await loadOverview();
      setMessage('Dados de demonstração carregados e recalculados com sucesso.');
    } catch {
      setMessage('Erro ao carregar dados de demonstração.');
    } finally {
      setBusy(false);
    }
  };

  const handleSyncAll = async () => {
    setBusy(true);
    setMessage(null);
    try {
      await syncApi.syncAll();
      await loadOverview();
      setMessage('Todas as turmas foram sincronizadas.');
    } catch {
      setMessage('Erro ao sincronizar turmas.');
    } finally {
      setBusy(false);
    }
  };

  const summary = report?.summary || {};
  const hasCourses = Number(summary.total_turmas || 0) > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Panorama Geral (R18)</h1>
          <p className="text-sm text-slate-500">
            Visão executiva consolidada do Google Classroom e Portal Cotemig.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleSeedDemo}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Database className="h-4 w-4 text-emerald-600" />
            Carregar Dados Demo
          </button>
          <button
            onClick={handleSyncAll}
            disabled={busy || !hasCourses}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />
            Sincronizar Tudo
          </button>
        </div>
      </div>

      {message && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {message}
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Disciplinas Ativas"
          value={String(summary.total_turmas ?? 0)}
          icon={<BookOpen className="h-5 w-5 text-blue-600" />}
        />
        <KpiCard
          title="Alunos Mapeados"
          value={String(summary.total_alunos ?? 0)}
          icon={<Users className="h-5 w-5 text-emerald-600" />}
        />
        <KpiCard
          title="Aguardando Correção"
          value={String(summary.total_aguardando_correcao ?? 0)}
          icon={<ClipboardList className="h-5 w-5 text-amber-600" />}
        />
        <KpiCard
          title="Alunos em Risco"
          value={String(summary.total_em_risco ?? 0)}
          icon={<AlertTriangle className="h-5 w-5 text-rose-600" />}
        />
      </div>

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
          Carregando panorama...
        </div>
      ) : !hasCourses ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-slate-400" />
          <h3 className="mt-3 text-base font-semibold text-slate-900">
            Nenhuma turma sincronizada ainda
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Conecte suas contas ou clique em <strong>Carregar Dados Demo</strong> para explorar todas
            as funcionalidades e os 18 relatórios imediatamente.
          </p>
          <div className="mt-5 flex justify-center gap-3">
            <button
              onClick={handleSeedDemo}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            >
              Carregar Dados Demo
            </button>
            <button
              onClick={() => onNavigate('connections')}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Configurar Conexões
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5 lg:col-span-2">
            <h2 className="mb-4 text-base font-semibold text-slate-900">
              Desempenho vs. Taxa de Entrega por Turma
            </h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={report?.chart_data || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="aproveitamento" name="Aproveitamento (%)" fill="#0f172a" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="entrega" name="Taxa Entrega (%)" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="mb-4 text-base font-semibold text-slate-900">Turmas Monitoradas</h2>
            <div className="space-y-3">
              {(report?.rows || []).map((row, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-slate-200 p-3 hover:border-slate-300"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-medium text-slate-900">{String(row.course)}</div>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {String(row.students_count)} alunos
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-600">
                    <div>Média: <strong>{String(row.avg_percentage)}%</strong></div>
                    <div>Entrega: <strong>{String(row.delivery_rate)}%</strong></div>
                    <div>Risco: <strong className="text-rose-600">{String(row.at_risk)}</strong></div>
                  </div>
                  {typeof row.course_id === 'number' && (
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => {
                          onSelectCourse(row.course_id as number);
                          onNavigate('gradebook');
                        }}
                        className="text-xs font-medium text-blue-600 hover:underline"
                      >
                        Abrir Grade →
                      </button>
                      <button
                        onClick={() => {
                          onSelectCourse(row.course_id as number);
                          onNavigate('rules');
                        }}
                        className="text-xs font-medium text-slate-600 hover:underline"
                      >
                        Configurar Temas
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function KpiCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-500">{title}</span>
        {icon}
      </div>
      <div className="mt-2 text-2xl font-bold text-slate-900">{value}</div>
    </div>
  );
}

