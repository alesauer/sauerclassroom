import { useEffect, useState } from 'react';
import { GitCompare, Plus, RefreshCw, UserCheck } from 'lucide-react';
import { syncApi } from '../api/client';
import type { CourseItem } from '../types';

interface StudentRow {
  id: number;
  classroom_user_id: string | null;
  cotemig_ra: string | null;
  full_name: string;
  email: string | null;
  status_cotemig: string;
  match_method: string;
}

export function CourseMapping({
  selectedCourseId,
  onSelectCourse,
}: {
  selectedCourseId: number | null;
  onSelectCourse: (id: number) => void;
}) {
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCotemigId, setNewCotemigId] = useState('COT-3A-POO-2026');
  const [raEdits, setRaEdits] = useState<Record<number, string>>({});
  const [syncing, setSyncing] = useState(false);

  const loadCourses = async () => {
    const list = await syncApi.listCourses();
    setCourses(list);
    if (list.length > 0 && !selectedCourseId) {
      onSelectCourse(list[0].id);
    }
  };

  const loadStudents = async (cid: number) => {
    const list = await syncApi.listStudents(cid);
    setStudents(list);
  };

  useEffect(() => {
    loadCourses();
  }, []);

  useEffect(() => {
    if (selectedCourseId) {
      loadStudents(selectedCourseId);
    }
  }, [selectedCourseId]);

  const handleCreateMapping = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCourseName.trim()) return;
    const res = await syncApi.createMapping({
      name: newCourseName,
      cotemig_class_id: newCotemigId,
    });
    setNewCourseName('');
    await loadCourses();
    onSelectCourse(res.id);
  };

  const handleSyncCourse = async () => {
    if (!selectedCourseId) return;
    setSyncing(true);
    try {
      await syncApi.syncCourse(selectedCourseId);
      await loadStudents(selectedCourseId);
    } finally {
      setSyncing(false);
    }
  };

  const handleSaveRa = async (studentId: number) => {
    if (!selectedCourseId) return;
    const ra = raEdits[studentId];
    if (!ra) return;
    await syncApi.linkStudent(selectedCourseId, {
      student_map_id: studentId,
      cotemig_ra: ra,
      status_cotemig: 'ATIVO',
    });
    await loadStudents(selectedCourseId);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Vínculo De/Para (RF05)</h1>
          <p className="text-sm text-slate-500">
            Associe turmas do Google Classroom às pautas do Cotemig e resolva alunos órfãos.
          </p>
        </div>
        {selectedCourseId && (
          <button
            onClick={handleSyncCourse}
            disabled={syncing}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
            Sincronizar Turma Selecionada
          </button>
        )}
      </div>

      {/* Criar vínculo rápido */}
      <form
        onSubmit={handleCreateMapping}
        className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4"
      >
        <div className="min-w-[220px] flex-1">
          <label className="block text-xs font-medium text-slate-700">Nome da Disciplina</label>
          <input
            type="text"
            value={newCourseName}
            onChange={(e) => setNewCourseName(e.target.value)}
            placeholder="Ex: Desenvolvimento Web - 3º Ano"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="w-56">
          <label className="block text-xs font-medium text-slate-700">ID Turma Cotemig</label>
          <input
            type="text"
            value={newCotemigId}
            onChange={(e) => setNewCotemigId(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          <Plus className="h-4 w-4" />
          Vincular Turma
        </button>
      </form>

      {/* Seletor de turma */}
      {courses.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {courses.map((c) => (
            <button
              key={c.id}
              onClick={() => onSelectCourse(c.id)}
              className={`inline-flex items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium transition ${
                selectedCourseId === c.id
                  ? 'border-slate-900 bg-slate-900 text-white'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              <GitCompare className="h-4 w-4" />
              {c.name}
            </button>
          ))}
        </div>
      )}

      {/* Tabela de conciliação */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Aluno</th>
                <th className="px-4 py-3">E-mail Institucional</th>
                <th className="px-4 py-3">RA Cotemig</th>
                <th className="px-4 py-3">Método</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {students.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{s.full_name}</td>
                  <td className="px-4 py-3 text-slate-600">{s.email || '-'}</td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      defaultValue={s.cotemig_ra || ''}
                      placeholder="Informar RA"
                      onChange={(e) => setRaEdits((prev) => ({ ...prev, [s.id]: e.target.value }))}
                      className="w-28 rounded border border-slate-300 px-2 py-1 text-xs"
                    />
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">{s.match_method}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        s.status_cotemig === 'ATIVO'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-amber-50 text-amber-700'
                      }`}
                    >
                      {s.status_cotemig}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleSaveRa(s.id)}
                      className="inline-flex items-center gap-1 rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
                    >
                      <UserCheck className="h-3.5 w-3.5" />
                      Vincular RA
                    </button>
                  </td>
                </tr>
              ))}
              {students.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Nenhum aluno carregado para esta turma.
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

