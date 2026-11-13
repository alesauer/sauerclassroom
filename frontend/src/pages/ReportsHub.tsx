import { useEffect, useState } from 'react';
import { Download, FileSpreadsheet, FileText } from 'lucide-react';
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
import type { CourseItem, ReportCatalogItem, ReportData } from '../types';

export function ReportsHub({
  selectedCourseId,
  onSelectCourse,
}: {
  selectedCourseId: number | null;
  onSelectCourse: (id: number) => void;
}) {
  const [catalog, setCatalog] = useState<ReportCatalogItem[]>([]);
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [activeCode, setActiveCode] = useState('R01');
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([reportsApi.getCatalog(), syncApi.listCourses()]).then(([cat, crs]) => {
      setCatalog(cat);
      setCourses(crs);
      if (crs.length > 0 && !selectedCourseId) {
        onSelectCourse(crs[0].id);
      }
    });
  }, []);

  useEffect(() => {
    setLoading(true);
    reportsApi
      .getReport(activeCode, selectedCourseId || undefined)
      .then(setReport)
      .catch(() => setReport(null))
      .finally(() => setLoading(false));
  }, [activeCode, selectedCourseId]);

  const categories = Array.from(new Set(catalog.map((c) => c.category)));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Central de Relatórios (R01–R18)</h1>
          <p className="text-sm text-slate-500">
            Consulte os 18 relatórios pedagógicos, de conciliação e operacionais com exportação imediata.
          </p>
        </div>

        {courses.length > 0 && (
          <select
            value={selectedCourseId || ''}
            onChange={(e) => onSelectCourse(Number(e.target.value))}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium"
          >
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Menu Lateral R01-R18 */}
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 lg:col-span-1">
          {categories.map((cat) => (
            <div key={cat}>
              <div className="mb-1.5 text-xs font-bold uppercase tracking-wider text-slate-400">
                {cat}
              </div>
              <div className="space-y-1">
                {catalog
                  .filter((item) => item.category === cat)
                  .map((item) => (
                    <button
                      key={item.code}
                      onClick={() => setActiveCode(item.code)}
                      className={`w-full rounded-lg px-2.5 py-2 text-left text-xs transition ${
                        activeCode === item.code
                          ? 'bg-slate-900 font-semibold text-white'
                          : 'text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      <span className="mr-1.5 font-mono opacity-75">{item.code}</span>
                      {item.title}
                    </button>
                  ))}
              </div>
            </div>
          ))}
        </div>

        {/* Área do Relatório */}
        <div className="space-y-4 lg:col-span-3">
          {loading ? (
            <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
              Gerando relatório {activeCode}...
            </div>
          ) : !report ? (
            <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500">
              Carregue ou sincronize uma turma para visualizar os relatórios.
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-xs font-bold text-white">
                        {report.code}
                      </span>
                      <h2 className="text-lg font-bold text-slate-900">{report.title}</h2>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{report.description}</p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <a
                      href={reportsApi.getExportUrl(
                        report.code,
                        'xlsx',
                        selectedCourseId || undefined
                      )}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-600 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                    >
                      <FileSpreadsheet className="h-4 w-4" />
                      Excel (.xlsx)
                    </a>
                    <a
                      href={reportsApi.getExportUrl(
                        report.code,
                        'csv',
                        selectedCourseId || undefined
                      )}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      <Download className="h-4 w-4" />
                      CSV
                    </a>
                    <a
                      href={reportsApi.getExportUrl(
                        report.code,
                        'pdf',
                        selectedCourseId || undefined
                      )}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-rose-600 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                    >
                      <FileText className="h-4 w-4" />
                      PDF
                    </a>
                  </div>
                </div>

                {Object.keys(report.summary).length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-3">
                    {Object.entries(report.summary).map(([k, v]) => (
                      <div key={k} className="rounded-lg bg-slate-50 px-3 py-1.5 text-xs">
                        <span className="text-slate-500">{k.replace(/_/g, ' ')}: </span>
                        <strong className="text-slate-900">{String(v)}</strong>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {report.chart_data.length > 0 && (
                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={report.chart_data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Legend />
                        {Object.keys(report.chart_data[0])
                          .filter((k) => k !== 'name')
                          .map((key, idx) => (
                            <Bar
                              key={key}
                              dataKey={key}
                              fill={['#0f172a', '#10b981', '#f59e0b'][idx % 3]}
                              radius={[4, 4, 0, 0]}
                            />
                          ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                      <tr>
                        {report.columns.map((c) => (
                          <th key={c.key} className="px-4 py-3">
                            {c.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {report.rows.map((r, rIdx) => (
                        <tr key={rIdx} className="hover:bg-slate-50">
                          {report.columns.map((c) => (
                            <td key={c.key} className="px-4 py-2.5 text-slate-800">
                              {String(r[c.key] ?? '-')}
                            </td>
                          ))}
                        </tr>
                      ))}
                      {report.rows.length === 0 && (
                        <tr>
                          <td
                            colSpan={report.columns.length}
                            className="px-4 py-8 text-center text-slate-500"
                          >
                            Nenhum registro encontrado para este critério.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

