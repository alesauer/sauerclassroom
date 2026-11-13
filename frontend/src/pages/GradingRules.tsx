import { useEffect, useState } from 'react';
import { Plus, Save, SlidersHorizontal } from 'lucide-react';
import { rulesApi, syncApi } from '../api/client';
import type { ActivityItem, CourseItem, GradebookResponse, ThemeItem } from '../types';

export function GradingRules({
  selectedCourseId,
  onSelectCourse,
}: {
  selectedCourseId: number | null;
  onSelectCourse: (id: number) => void;
}) {
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [gradebook, setGradebook] = useState<GradebookResponse | null>(null);
  const [themes, setThemes] = useState<ThemeItem[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [minPassing, setMinPassing] = useState(60);
  const [useDrafts, setUseDrafts] = useState(false);
  const [newThemeTitle, setNewThemeTitle] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const loadGradebook = async (cid: number) => {
    const gb = await rulesApi.getGradebook(cid);
    setGradebook(gb);
    setThemes(gb.themes.filter((t) => t.id !== null));
    setActivities(gb.activities);
    setMinPassing(gb.course.min_passing_grade);
    setUseDrafts(gb.course.use_draft_grades);
  };

  useEffect(() => {
    syncApi.listCourses().then((list) => {
      setCourses(list);
      if (list.length > 0) {
        const cid = selectedCourseId || list[0].id;
        if (!selectedCourseId) onSelectCourse(cid);
        loadGradebook(cid);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedCourseId) {
      loadGradebook(selectedCourseId);
    }
  }, [selectedCourseId]);

  const handleSaveRules = async () => {
    if (!selectedCourseId) return;
    setSaving(true);
    setSavedMsg(null);
    try {
      const updated = await rulesApi.updateRules(selectedCourseId, {
        min_passing_grade: minPassing,
        use_draft_grades: useDrafts,
        themes: themes.map((t, idx) => ({
          id: t.id,
          title: t.title,
          max_points_cap: t.max_points_cap,
          rounding_rule: t.rounding_rule,
          order_index: idx + 1,
        })),
        activities: activities.map((a) => ({
          id: a.id,
          theme_id: a.theme_id,
          custom_points_weight: Number(a.custom_points_weight) || 0,
          include_in_calc: a.include_in_calc,
        })),
      });
      setGradebook(updated);
      setThemes(updated.themes.filter((t) => t.id !== null));
      setActivities(updated.activities);
      setSavedMsg('Critérios salvos e notas recalculadas com sucesso!');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateTheme = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourseId || !newThemeTitle.trim()) return;
    await rulesApi.createTheme(selectedCourseId, {
      title: newThemeTitle,
      max_points_cap: 10,
      rounding_rule: 'decimal_1',
      order_index: themes.length + 1,
    });
    setNewThemeTitle('');
    await loadGradebook(selectedCourseId);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Critérios e Pontos por Tema (RF08)</h1>
          <p className="text-sm text-slate-500">
            Defina pesos personalizados por atividade, tetos máximos e regras de arredondamento por tema.
          </p>
        </div>
        <button
          onClick={handleSaveRules}
          disabled={saving || !selectedCourseId}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {saving ? 'Recalculando...' : 'Salvar e Recalcular Notas'}
        </button>
      </div>

      {savedMsg && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {savedMsg}
        </div>
      )}

      {courses.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <SlidersHorizontal className="h-4 w-4 text-slate-500" />
          <select
            value={selectedCourseId || ''}
            onChange={(e) => onSelectCourse(Number(e.target.value))}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium"
          >
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <label className="ml-4 flex items-center gap-2 text-sm text-slate-700">
            Média Mínima (%):
            <input
              type="number"
              value={minPassing}
              onChange={(e) => setMinPassing(Number(e.target.value))}
              className="w-20 rounded border border-slate-300 px-2 py-1 text-sm"
            />
          </label>

          <label className="ml-4 flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={useDrafts}
              onChange={(e) => setUseDrafts(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Considerar notas em rascunho (draftGrade)
          </label>

          <div className="ml-auto text-sm font-semibold text-slate-900">
            Total Distribuído: {gradebook?.course.total_possible_points ?? 0} pts
          </div>
        </div>
      )}

      {/* Temas */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-slate-900">Temas / Blocos Avaliativos</h2>
          <form onSubmit={handleCreateTheme} className="flex gap-2">
            <input
              type="text"
              value={newThemeTitle}
              onChange={(e) => setNewThemeTitle(e.target.value)}
              placeholder="Novo tema..."
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            />
            <button
              type="submit"
              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
            >
              <Plus className="h-4 w-4" />
              Adicionar Tema
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {themes.map((t, idx) => (
            <div key={t.id ?? idx} className="rounded-lg border border-slate-200 p-4 space-y-3">
              <input
                type="text"
                value={t.title}
                onChange={(e) =>
                  setThemes((prev) =>
                    prev.map((item, i) => (i === idx ? { ...item, title: e.target.value } : item))
                  )
                }
                className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm font-medium"
              />
              <div className="grid grid-cols-2 gap-2 text-xs">
                <label className="block text-slate-600">
                  Teto Máximo (pts)
                  <input
                    type="number"
                    step="0.5"
                    value={t.max_points_cap ?? ''}
                    placeholder="Sem teto"
                    onChange={(e) =>
                      setThemes((prev) =>
                        prev.map((item, i) =>
                          i === idx
                            ? {
                                ...item,
                                max_points_cap: e.target.value ? Number(e.target.value) : null,
                              }
                            : item
                        )
                      )
                    }
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  />
                </label>
                <label className="block text-slate-600">
                  Arredondamento
                  <select
                    value={t.rounding_rule}
                    onChange={(e) =>
                      setThemes((prev) =>
                        prev.map((item, i) =>
                          i === idx ? { ...item, rounding_rule: e.target.value } : item
                        )
                      )
                    }
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  >
                    <option value="decimal_1">1 casa decimal</option>
                    <option value="half_point">Meio em meio (0.5)</option>
                    <option value="integer">Nota inteira</option>
                    <option value="none">Exato (2 casas)</option>
                  </select>
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Atividades */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-3">
          <h2 className="text-base font-semibold text-slate-900">
            Atividades Importadas e Pesos em Pontos
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Atividade</th>
                <th className="px-4 py-3">Tema Vinculado</th>
                <th className="px-4 py-3">Max Classroom</th>
                <th className="px-4 py-3">Peso no Sistema (pts)</th>
                <th className="px-4 py-3">Incluir no Cálculo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {activities.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{a.title}</td>
                  <td className="px-4 py-3">
                    <select
                      value={a.theme_id ?? ''}
                      onChange={(e) =>
                        setActivities((prev) =>
                          prev.map((item) =>
                            item.id === a.id
                              ? {
                                  ...item,
                                  theme_id: e.target.value ? Number(e.target.value) : null,
                                }
                              : item
                          )
                        )
                      }
                      className="rounded border border-slate-300 px-2 py-1 text-xs"
                    >
                      <option value="">Sem Tema</option>
                      {themes.map((t) => (
                        <option key={t.id} value={t.id ?? ''}>
                          {t.title}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{a.classroom_max_points}</td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      step="0.5"
                      value={a.custom_points_weight}
                      onChange={(e) =>
                        setActivities((prev) =>
                          prev.map((item) =>
                            item.id === a.id
                              ? { ...item, custom_points_weight: Number(e.target.value) }
                              : item
                          )
                        )
                      }
                      className="w-24 rounded border border-slate-300 px-2 py-1 text-sm font-medium"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={a.include_in_calc}
                      onChange={(e) =>
                        setActivities((prev) =>
                          prev.map((item) =>
                            item.id === a.id ? { ...item, include_in_calc: e.target.checked } : item
                          )
                        )
                      }
                      className="h-4 w-4 rounded border-slate-300"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

