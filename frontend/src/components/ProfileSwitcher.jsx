import React, { useEffect, useRef, useState } from 'react';
import { X, Check, Lock } from 'lucide-react';
import { api, post } from '../api';

export default function ProfileSwitcher({ user, onClose, onSelect }) {
  const dialog = useRef(null);
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const load = () => {
    setLoading(true); setError('');
    api('/auth/profiles').then(setProfiles).catch(e => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => {
    dialog.current.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    load();
    return () => { document.body.style.overflow = overflow; };
  }, []);
  const submit = async e => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const next = await post('/auth/login', { username: selected.username, password });
      setPassword(''); onSelect(next);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  return <dialog ref={dialog} aria-labelledby="profile-heading"
    onCancel={e => { e.preventDefault(); if (!busy) onClose(); }}
    className="m-auto w-[calc(100%_-_2rem)] max-w-2xl max-h-[85vh] overflow-y-auto rounded-3xl border border-white/20 bg-canvas p-6 text-white backdrop:bg-black/80">
    <header className="flex items-center justify-between gap-4 mb-3">
      <h2 id="profile-heading" className="text-2xl font-semibold">Choose a profile</h2>
      <button type="button" aria-label="Close profiles" disabled={busy} onClick={onClose} className="p-2"><X /></button>
    </header>
    <p className="text-white/60 mb-6">Each profile has its own watch history, ratings, and saved progress.</p>
    {loading ? <p role="status">Loading profiles…</p> : <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {profiles.map(profile => <button key={profile.id} type="button" disabled={busy}
        aria-pressed={(selected?.id ?? user.id) === profile.id}
        onClick={() => { setError(''); setPassword(''); if (profile.id === user.id) onClose(); else setSelected(profile); }}
        className={'flex flex-col items-center gap-2 rounded-2xl border p-4 min-w-0 ' +
          ((selected?.id ?? user.id) === profile.id ? 'border-accent bg-accent/10' : 'border-white/15 bg-white/5 hover:bg-white/10')}>
        <span className="profile-avatar profile-avatar-large">{profile.username[0].toUpperCase()}</span>
        <span className="w-full break-words font-medium">{profile.username}</span>
        <span className="text-xs text-white/60">{profile.is_admin ? 'Administrator' : 'Viewer'}</span>
        {profile.id === user.id && <span className="flex items-center gap-1 text-xs text-accent-soft"><Check size={14} />Current profile</span>}
      </button>)}
    </div>}
    {selected && <form onSubmit={submit} className="mt-6 space-y-3">
      <label className="block">Password for {selected.username}
        <input key={selected.id} autoFocus required type="password" autoComplete="current-password"
          minLength={10} maxLength={128} value={password} disabled={busy}
          onChange={e => setPassword(e.target.value)} className="mt-2 w-full rounded-xl border border-white/20 bg-black/40 p-3" />
      </label>
      <input type="text" name="username" autoComplete="username" value={selected.username} readOnly hidden />
      <button disabled={busy} className="flex items-center justify-center gap-2 w-full rounded-xl bg-accent-strong p-3 disabled:opacity-50">
        <Lock size={16} />{busy ? 'Switching…' : 'Switch to ' + selected.username}
      </button>
    </form>}
    {error && <p role="alert" className="mt-4 text-red-300">{error}
      {!profiles.length && <button onClick={load} className="ml-3 underline">Retry</button>}
    </p>}
  </dialog>;
}
