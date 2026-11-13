import { useEffect, useState } from 'react';
import { CheckCircle2, KeyRound, Link2, LogOut, ShieldCheck, XCircle } from 'lucide-react';
import { authApi, syncApi } from '../api/client';
import type { AuthStatusResponse } from '../types';

export function Connections() {
  const [status, setStatus] = useState<AuthStatusResponse | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);
  const [history, setHistory] = useState<
    { id: number; source: string; status: string; details: string; synced_at: string }[]
  >([]);

  const loadAll = async () => {
    try {
      const [st, hist] = await Promise.all([authApi.getStatus(), syncApi.getHistory()]);
      setStatus(st);
      setHistory(hist);
    } catch {
      setFeedback({ type: 'err', text: 'Não foi possível consultar o backend FastAPI.' });
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleGoogleConnect = async () => {
    setFeedback(null);
    try {
      const { url } = await authApi.getGoogleUrl();
      window.open(url, '_blank', 'noopener,noreferrer');
      setFeedback({
        type: 'ok',
        text: 'Janela de login OAuth 2.0 aberta. Após autorizar, recarregue o status.',
      });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao gerar URL OAuth do Google.';
      setFeedback({ type: 'err', text: detail });
    }
  };

  const handleCotemigLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    try {
      await authApi.loginCotemig(username, password);
      setPassword('');
      setFeedback({
        type: 'ok',
        text: 'Sessão do Portal Cotemig autenticada e salva com criptografia Fernet.',
      });
      await loadAll();
    } catch {
      setFeedback({ type: 'err', text: 'Falha ao autenticar no Portal Cotemig.' });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Conexões e Credenciais (RF01–RF03)</h1>
        <p className="text-sm text-slate-500">
          Tokens OAuth e sessões ficam isolados localmente no volume{' '}
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">/credentials</code>.
        </p>
      </div>

      {feedback && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            feedback.type === 'ok'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
              : 'border-rose-200 bg-rose-50 text-rose-800'
          }`}
        >
          {feedback.text}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Google Classroom */}
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-50 p-2.5 text-blue-600">
                <Link2 className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-900">Google Classroom (OAuth 2.0)</h2>
                <p className="text-xs text-slate-500">Importação de turmas, tópicos, tarefas e entregas</p>
              </div>
            </div>
            <StatusBadge
              connected={Boolean(status?.google_classroom.connected)}
              label={status?.google_classroom.status || 'Verificando'}
            />
          </div>

          <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            <p>
              <strong>Conta:</strong> {status?.google_classroom.account || 'Não conectado'}
            </p>
            <p className="mt-1">{status?.google_classroom.details}</p>
          </div>

          <div className="mt-5 flex gap-2">
            <button
              onClick={handleGoogleConnect}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Conectar Google Classroom
            </button>
            {status?.google_classroom.connected && (
              <button
                onClick={async () => {
                  await authApi.disconnectGoogle();
                  await loadAll();
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                <LogOut className="h-4 w-4" />
                Desconectar
              </button>
            )}
          </div>
        </div>

        {/* Portal Cotemig */}
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-50 p-2.5 text-emerald-600">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-slate-900">Portal Acadêmico Cotemig</h2>
                <p className="text-xs text-slate-500">
                  Adapter isolado ({status?.cotemig_portal.mode || 'mock'}) com sessão cifrada
                </p>
              </div>
            </div>
            <StatusBadge
              connected={Boolean(status?.cotemig_portal.connected)}
              label={status?.cotemig_portal.status || 'Verificando'}
            />
          </div>

          <form onSubmit={handleCotemigLogin} className="mt-4 space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-700">Usuário / E-mail Professor</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="prof.sauer@cotemig.com.br"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Senha do Portal</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                <KeyRound className="h-4 w-4" />
                Autenticar no Portal
              </button>
              {status?.cotemig_portal.connected && (
                <button
                  type="button"
                  onClick={async () => {
                    await authApi.logoutCotemig();
                    await loadAll();
                  }}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                >
                  Encerrar Sessão
                </button>
              )}
            </div>
          </form>
        </div>
      </div>

      {/* Histórico */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="mb-3 text-base font-semibold text-slate-900">Histórico de Sincronizações</h3>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhuma sincronização registrada.</p>
        ) : (
          <div className="divide-y divide-slate-100 text-sm">
            {history.map((h) => (
              <div key={h.id} className="flex flex-wrap items-center justify-between py-2.5">
                <div>
                  <span className="font-medium text-slate-800">{h.details}</span>
                  <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    {h.source}
                  </span>
                </div>
                <span className="text-xs text-slate-500">{h.synced_at.slice(0, 19).replace('T', ' ')}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ connected, label }: { connected: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
        connected ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'
      }`}
    >
      {connected ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
      {label}
    </span>
  );
}

