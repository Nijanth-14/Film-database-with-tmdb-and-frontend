import { sheetMotion } from '../motion';
import { motion } from 'framer-motion';
import React, { useEffect, useState } from 'react';
import { X, Play, Check } from 'lucide-react';
import { api } from '../api';
import MovieDetails from './MovieDetails';

export default function SeriesModal({ media, user, onClose, onPlay }) {
  const [series, setSeries] = useState(null);
  const [season, setSeason] = useState(null);
  const [detail, setDetail] = useState(media);
  const [error, setError] = useState('');
  useEffect(() => {
    let cancelled = false, timer;
    document.body.style.overflow = 'hidden';
    const load = async () => {
      try {
        const data = await api('/series/' + media.id);
        if (cancelled) return;
        setSeries(data);
        setSeason(current => data.season_numbers.includes(current) ? current :
          data.episodes.find(e => e.id === data.resume_episode_id)?.season_number ?? data.season_numbers[0]);
        timer = setTimeout(load, 4000);
      } catch (e) { if (!cancelled) setError(e.message); }
    };
    load();
    return () => { cancelled = true; clearTimeout(timer); document.body.style.overflow = ''; };
  }, [media.id]);
  const next = series?.episodes.find(e => e.id === series.resume_episode_id);
  const play = episode => onPlay({ ...episode, title: detail.title,
    resumeAt: episode.last_position, poster_path: detail.poster_path });
  const label = episode => episode.episode_number == null ? episode.filename :
    'Episode ' + episode.episode_number;
  return <div className="fixed inset-0 z-[10000] bg-black/85 flex items-center justify-center p-4"
    role="dialog" aria-modal="true" aria-label={detail.title + ' seasons and episodes'}>
    <motion.section {...sheetMotion} className="w-full max-w-4xl max-h-[92vh] overflow-y-auto bg-canvas border border-white/15 rounded-3xl p-5 md:p-8">
      <header className="flex justify-between items-center gap-4 mb-5">
        <h2 className="text-2xl font-bold text-white">{detail.title}</h2>
        <button aria-label="Close series" onClick={onClose} className="p-2"><X /></button>
      </header>
      <MovieDetails mediaId={media.id} user={user} onUpdate={setDetail} />
      {error && <p role="alert" className="text-red-200">{error}</p>}
      {!series && !error && <p role="status">Loading episodes…</p>}
      {series && <>
        <div className="flex flex-wrap justify-between items-center gap-4 mb-5">
          <label className="text-white">Season
            <select aria-label="Season" value={season ?? ''} onChange={e => setSeason(Number(e.target.value))}
              className="ml-3 rounded-lg bg-elevated p-3">
              {series.season_numbers.map(number => <option key={number} value={number}>
                {number === 0 ? 'Specials' : 'Season ' + number}
              </option>)}
            </select>
          </label>
          {next && <button onClick={() => play(next)} className="flex items-center gap-2 bg-accent-strong rounded-xl px-4 py-3 text-white">
            <Play size={16} />{next.last_position > 0 ? 'Continue' : 'Play'} S{next.season_number} · {label(next)}
          </button>}
        </div>
        <div className="space-y-3">
          {series.episodes.filter(e => e.season_number === season).map(episode =>
            <button key={episode.id} onClick={() => play(episode)}
              className="block w-full text-left p-4 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10">
              <div className="flex justify-between items-center gap-4">
                <div className="min-w-0">
                  <p className="text-white font-semibold">{label(episode)}</p>
                  <p className="text-xs text-white/50 truncate mt-1">{episode.filename}</p>
                  <p className="text-sm text-white/70 mt-2">{Math.round(episode.duration / 60)} min
                    {episode.last_position > 0 ? ' · Resume at ' + Math.floor(episode.last_position / 60) + ':' + String(Math.floor(episode.last_position % 60)).padStart(2,'0') : ''}
                    {episode.watched ? ' · Watched' : ''}
                    {episode.playback_status === 'preparing' ? ' · Preparing ' + Math.floor(episode.prepare_progress || 0) + '%' : ''}
                  </p>
                </div>
                {episode.watched ? <Check className="text-green-300 shrink-0" /> : <Play className="shrink-0" size={20} />}
              </div>
              {episode.last_position > 0 && <progress max={episode.duration} value={episode.last_position} className="w-full h-1 mt-3" />}
            </button>)}
        </div>
      </>}
    </motion.section>
  </div>;
}
