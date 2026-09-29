import { Star } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { api, post } from '../api';

const art = (path, size = 'w500') => path ? 'https://image.tmdb.org/t/p/' + size + path : undefined;
export default function MovieDetails({ mediaId, user, onUpdate }) {
  const [item, setItem] = useState(null);
  const [query, setQuery] = useState('');
  const [matching, setMatching] = useState(false);
  const [matches, setMatches] = useState([]);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let stopped = false, timer;
    const load = async () => {
      try {
        const next = await api('/catalog/' + mediaId);
        if (stopped) return;
        setItem(next); onUpdate(next);
        if (['pending','processing'].includes(next.metadata_status)) timer = setTimeout(load, 2500);
      } catch (e) { if (!stopped) setError(e.message); }
    };
    load();
    return () => { stopped = true; clearTimeout(timer); };
  }, [mediaId, revision, onUpdate]);
  const search = async e => {
    e.preventDefault(); setBusy(true); setError('');
    try { setMatches(await api('/metadata/search?q=' + encodeURIComponent(query))); setSearched(true); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const choose = async match => {
    setBusy(true); setError('');
    try {
      await post('/catalog/' + mediaId + '/metadata', { tmdb_id: match.id, media_type: match.media_type });
      setMatching(false); setRevision(x => x + 1);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const retry = async () => {
    setBusy(true); setError('');
    try { await post('/catalog/' + mediaId + '/metadata/retry', {}); setRevision(x => x + 1); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  if (!item) return null;
  const status = {
    pending: 'Movie details queued…', processing: 'Fetching artwork and movie details…',
    failed: 'Movie details could not be fetched. Retry or search for the correct title.',
    not_found: 'No matching title found. Search using the movie or series name.',
    skipped: 'Online movie details have not been loaded yet.',
  }[item.metadata_status];
  return <section aria-label="Movie details" className="mb-6 rounded-2xl overflow-hidden border border-white/10">
    <div className="relative p-5 bg-surface">
      {item.backdrop_path && <img src={art(item.backdrop_path, 'w1280')} alt="" className="absolute inset-0 w-full h-full object-cover opacity-20" />}
      <div className="relative flex gap-5 items-start">
        {item.poster_path && <img src={art(item.poster_path)} alt={item.title + ' cover'}
          className="w-24 sm:w-36 rounded-xl shadow-xl shrink-0" />}
        <div className="min-w-0 space-y-3">
          <h3 className="text-xl font-bold text-white">{item.title}</h3>
          <div className="flex flex-wrap gap-3 text-sm text-white/80">
            {item.tmdb_rating != null && <span className="inline-flex items-center gap-1.5 text-accent-soft font-semibold"><Star size={15} aria-hidden="true" /> {Number(item.tmdb_rating).toFixed(1)} / 10 · TMDB</span>}
            {item.genre && <span>{item.genre}</span>}
            {item.language && <span>{item.language}</span>}
            <span>{Math.round(item.duration / 60)} min</span>
          </div>
          <p className="text-white/80 text-sm leading-relaxed">{item.overview || 'Synopsis is not available yet.'}</p>
          {item.studio && <p className="text-white/65 text-sm"><strong>Studio:</strong> {item.studio}</p>}
          {item.actors?.length > 0 && <p className="text-white/80 text-sm"><strong>Cast:</strong> {item.actors.join(', ')}</p>}
        </div>
      </div>
    </div>
    <div className="p-4 bg-canvas space-y-3">
      {status && <p role="status" className="text-sm text-amber-200">{status}</p>}
      {user.is_admin && <div className="flex gap-4 text-sm">
        <button disabled={busy} onClick={() => { setMatching(!matching); setQuery(item.title); }} className="text-accent-soft underline">
          {item.tmdb_rating != null ? 'Correct movie match' : 'Find movie details'}
        </button>
        <button disabled={busy || ['pending','processing'].includes(item.metadata_status)} onClick={retry} className="text-accent-soft underline disabled:opacity-40">Refresh details</button>
      </div>}
      {matching && <div>
        <form onSubmit={search} className="flex gap-2">
          <input aria-label="Movie or series title" required minLength={2} value={query} onChange={e => setQuery(e.target.value)}
            className="min-w-0 flex-1 p-2 bg-elevated rounded-lg text-white" placeholder="Movie or series title" />
          <button disabled={busy} className="bg-accent-strong text-white rounded-lg px-4">{busy ? 'Loading…' : 'Search'}</button>
        </form>
        {searched && matches.length === 0 && !busy && <p className="text-sm text-white/60 mt-3">No matches found. Try the full movie or series title.</p>}
        <div className="max-h-72 overflow-y-auto mt-3 space-y-2">
          {matches.map(match => <button key={match.media_type + match.id} disabled={busy} onClick={() => choose(match)}
            className="flex gap-3 text-left w-full p-3 rounded-lg bg-white/5 hover:bg-white/10">
            {match.poster_path && <img src={art(match.poster_path, 'w92')} alt="" className="w-10 rounded" />}
            <span><strong className="text-white">{match.title}</strong>
              <span className="block text-xs text-white/60">{match.media_type === 'tv' ? 'Series' : 'Movie'} · {match.date || 'Date unavailable'}</span>
              <span className="block text-xs text-white/60 line-clamp-2">{match.overview}</span>
            </span>
          </button>)}
        </div>
      </div>}
      {error && <p role="alert" className="text-red-200 text-sm">{error}</p>}
      <p className="text-xs text-white/40">Movie information and artwork provided by TMDB.</p>
    </div>
  </section>;
}
