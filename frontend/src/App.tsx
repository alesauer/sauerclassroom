import { useState } from 'react';
import {
  BarChart3,
  BookCheck,
  GitCompare,
  GraduationCap,
  LayoutDashboard,
  Link2,
  Menu,
  Sliders,
  X,
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSelectTab = (id: string) => {
    setActiveTab(id);
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {/* Overlay mobile */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-xs md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-200 md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Marca */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white">
              <GraduationCap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-bold leading-tight tracking-tight text-slate-900">
                SauerClassroom
              </div>
              <div className="text-[11px] font-medium text-slate-500">
                Classroom + Cotemig
              </div>
            </div>
          </div>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 md:hidden"
            aria-label="Fechar menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Links de navegação */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleSelectTab(item.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  active
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Rodapé da Sidebar */}
        <div className="border-t border-slate-200 p-4">
          <div className="rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
            <div className="font-semibold">Modo Local-First (LGPD)</div>
            <div className="mt-0.5 text-[11px] text-emerald-700">
              SQLite & sessões cifradas no host
            </div>
          </div>
        </div>
      </aside>

      {/* Área principal */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Barra superior apenas no mobile */}
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
              <GraduationCap className="h-4 w-4" />
            </div>
            <span className="text-sm font-bold text-slate-900">SauerClassroom</span>
          </div>
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="rounded-lg border border-slate-200 p-2 text-slate-700 hover:bg-slate-50"
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {activeTab === 'dashboard' && (
            <Dashboard onSelectCourse={setSelectedCourseId} onNavigate={setActiveTab} />
          )}
          {activeTab === 'gradebook' && (
            <Gradebook selectedCourseId={selectedCourseId} onSelectCourse={setSelectedCourseId} />
          )}
          {activeTab === 'rules' && (
            <GradingRules
              selectedCourseId={selectedCourseId}
              onSelectCourse={setSelectedCourseId}
            />
          )}
          {activeTab === 'reports' && (
            <ReportsHub selectedCourseId={selectedCourseId} onSelectCourse={setSelectedCourseId} />
          )}
          {activeTab === 'mapping' && (
            <CourseMapping
              selectedCourseId={selectedCourseId}
              onSelectCourse={setSelectedCourseId}
            />
          )}
          {activeTab === 'connections' && <Connections />}
        </main>
      </div>
    </div>
  );
}
