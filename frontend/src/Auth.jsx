import React, { useEffect, useState } from 'react';
import App from './App';
import { api, post } from './api';

export default function Auth() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [register, setRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api('/auth/me').then(setUser).catch(() => {}).finally(() => setChecking(false));
    const expired = () => { setUser(null); setError('Session expired. Please sign in again.'); };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, []);
  const submit = async event => {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      setUser(await post(register ? '/auth/register' : '/auth/login', { username, password }));
      setPassword('');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const logout = async () => {
    try { await post('/auth/logout', {}); setUser(null); }
    catch (e) { window.alert(e.message); }
  };
  if (checking) return <main className="min-h-screen grid place-items-center text-white">Opening your library…</main>;
  if (user) return <App key={user.id} user={user} onLogout={logout} onProfileChange={setUser} />;
  return <main className="min-h-screen flex items-center justify-center p-6">
    <div className="forest-bg" />
    <form onSubmit={submit} className="relative w-full max-w-md glass rounded-3xl p-8 space-y-5">
      <p className="text-sm tracking-widest text-accent">STREAM · YOUR LOCAL LIBRARY</p>
      <h1 className="text-3xl font-bold text-white">{register ? 'Create an account' : 'Welcome back'}</h1>
      <p className="text-white/70">Browse, play, and pick up where you left off.</p>
      <label className="block text-white">Username
        <input required minLength={3} maxLength={100} pattern="[a-zA-Z0-9_.-]+"
          autoComplete="username" value={username} onChange={e => setUsername(e.target.value)}
          className="mt-2 w-full bg-black/40 rounded-xl p-3 border border-white/20" />
      </label>
      <label className="block text-white">Password
        <input required type="password" minLength={10} maxLength={128}
          autoComplete={register ? 'new-password' : 'current-password'}
          value={password} onChange={e => setPassword(e.target.value)}
          className="mt-2 w-full bg-black/40 rounded-xl p-3 border border-white/20" />
      </label>
      {register && <p className="text-xs text-white/60">Use at least 10 characters. Usernames can contain letters, numbers, dots, underscores and hyphens.</p>}
      {error && <p role="alert" className="text-red-300">{error}</p>}
      <button disabled={busy} className="w-full rounded-xl bg-accent-strong p-3 text-white font-semibold disabled:opacity-50">
        {busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}
      </button>
      <button type="button" onClick={() => { setRegister(!register); setError(''); }}
        className="w-full text-accent-soft text-sm">
        {register ? 'Already have an account? Sign in' : 'New here? Create an account'}
      </button>
    </form>
  </main>;
}
