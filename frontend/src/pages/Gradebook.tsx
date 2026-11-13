import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { rulesApi, syncApi } from '../api/client';
import type { CourseItem, GradebookResponse } from '../types';

export function Gradebook({
  selectedCourseId,
  onSelectCourse,
}: {
  selectedCourseId: number | null;
  onSelectCourse: (id: number) => void;
}) {
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [gradebook, setGradebook] = useState<GradebookResponse | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  useEffect(() => {
    syncApi.listCourses().then((list) => {
      setCourses(list);
      if (list.length > 0) {
        const cid = selectedCourseId || list[0].id;
        if (!selectedCourseId) onSelectCourse(cid);
        rulesApi.getGradebook(cid).then(setGradebook);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedCourseId) {
      rulesApi.getGradebook(selectedCourseId).then(setGradebook);
    }
  }, [selectedCourseId]);

  const filteredStudents = useMemo(() => {
    if (!gradebook) return [];
    return gradebook.students.filter((s) => {
      const matchesName =
        s.full_name.toLowerCase().includes(search.toLowerCase()) ||
        (s.cotemig_ra || '').includes(search);
      const matchesStatus = statusFilter === 'ALL' || s.risk_status === statusFilter;
      return matchesName && matchesStatus;
    });
  }, [gradebook, search, statusFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Grade Analítica por Temas (RF12)</h1>
          <p className="text-sm text-slate-500">
            Soma por temas com tetos aplicados, taxa de entrega e auditoria rápida Cotemig.
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

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div className="relative min-w-[240px] flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar aluno por nome ou RA..."
            className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm focus:border-slate-900 focus:outline-none"
          />
        </div>

        <div className="flex gap-1.5">
          {[
            { id: 'ALL', label: 'Todos' },
            { id: 'APROVADO', label: 'Aprovados' },
            { id: 'ATENCAO', label: 'Atenção' },
            { id: 'RISCO', label: 'Em Risco' },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setStatusFilter(f.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                statusFilter === f.id
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabela */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">RA</th>
                <th className="px-4 py-3">Aluno</th>
                {gradebook?.themes.map((t) => (
                  <th key={String(t.id)} className="px-4 py-3">
                    {t.title}
                    <div className="text-[10px] font-normal text-slate-400">
                      máx {t.effective_possible} pts
                    </div>
                  </th>
                ))}
                <th className="px-4 py-3">
                  Total ({gradebook?.course.total_possible_points ?? 0})
                </th>
                <th className="px-4 py-3">Aprov. %</th>
                <th className="px-4 py-3">Entregas</th>
                <th className="px-4 py-3">Cotemig</th>
                <th className="px-4 py-3">Situação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredStudents.map((s) => (
                <tr key={s.student_map_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">
                    {s.cotemig_ra || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{s.full_name}</div>
                    <div className="text-xs text-slate-400">{s.email || '-'}</div>
                  </td>
                  {gradebook?.themes.map((t) => {
                    const key = t.id !== null ? String(t.id) : 'unthemed';
                    const score = s.theme_scores[key];
                    return (
                      <td key={key} className="px-4 py-3 font-medium text-slate-800">
                        {score ? score.final_points : 0}
                      </td>
                    );
                  })}
                  <td className="px-4 py-3 font-bold text-slate-900">{s.total_points}</td>
                  <td className="px-4 py-3">{s.percentage}%</td>
                  <td className="px-4 py-3 text-xs text-slate-600">
                    {s.submission_rate}% ({s.pending_count} pend.)
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {s.cotemig_official_grade !== null ? (
                      <span
                        className={
                          Math.abs(s.grade_divergence || 0) >= 0.1
                            ? 'font-semibold text-amber-600'
                            : 'text-emerald-700'
                        }
                      >
                        {s.cotemig_official_grade}
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        s.risk_status === 'APROVADO'
                          ? 'bg-emerald-50 text-emerald-700'
                          : s.risk_status === 'ATENCAO'
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-rose-50 text-rose-700'
                      }`}
                    >
                      {s.risk_status}
                    </span>
                  </td>
                </tr>
              ))}
              {filteredStudents.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-slate-500">
                    Nenhum aluno encontrado com os filtros atuais.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

