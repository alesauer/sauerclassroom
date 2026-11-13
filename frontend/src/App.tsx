import { useState } from 'react';
import {
  BarChart3,
  BookCheck,
  GitCompare,
  GraduationCap,
  LayoutDashboard,
  Link2,
  Sliders,
} from 'lucide-react';
import { Connections } from './pages/Connections';
import { CourseMapping } from './pages/CourseMapping';
import { Dashboard } from './pages/Dashboard';
import { Gradebook } from './pages/Gradebook';
import { GradingRules } from './pages/GradingRules';
import { ReportsHub } from './pages/ReportsHub';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Panorama Geral', icon: LayoutDashboard },
  { id: 'gradebook', label: 'Grade de Notas', icon: BookCheck },
  { id: 'rules', label: 'Critérios e Temas', icon: Sliders },
  { id: 'reports', label: 'Relatórios (R01–R18)', icon: BarChart3 },
  { id: 'mapping', label: 'Vínculo De/Para', icon: GitCompare },
  { id: 'connections', label: 'Conexões', icon: Link2 },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white">
              <GraduationCap className="h-5 w-5" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-slate-900">
                SauerClassroom
              </span>
              <span className="ml-2 hidden rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 sm:inline-block">
                Local-First LGPD
              </span>
            </div>
          </div>

          <nav className="flex flex-wrap gap-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden md:inline">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {activeTab === 'dashboard' && (
          <Dashboard onSelectCourse={setSelectedCourseId} onNavigate={setActiveTab} />
        )}
        {activeTab === 'gradebook' && (
          <Gradebook selectedCourseId={selectedCourseId} onSelectCourse={setSelectedCourseId} />
        )}
        {activeTab === 'rules' && (
          <GradingRules selectedCourseId={selectedCourseId} onSelectCourse={setSelectedCourseId} />
        )}
        {activeTab === 'reports' && (
          <ReportsHub selectedCourseId={selectedCourseId} onSelectCourse={setSelectedCourseId} />
        )}
        {activeTab === 'mapping' && (
          <CourseMapping selectedCourseId={selectedCourseId} onSelectCourse={setSelectedCourseId} />
        )}
        {activeTab === 'connections' && <Connections />}
      </main>
    </div>
  );
}

