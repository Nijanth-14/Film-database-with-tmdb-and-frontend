import { sheetMotion } from '../motion';
import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { X, Trash2 } from 'lucide-react';
import { api, post, API_BASE_URL } from '../api';
import ConfirmModal from './ConfirmModal';
import MovieDetails from './MovieDetails';

export default function PlayerModal({ media, user, onClose, onDelete, isPlaying, setIsPlaying, position, setPosition }) {
  const video = useRef(null);
  const session = useRef(null);
  const sequence = useRef(0);
  const completed = useRef(false);
  const lastSave = useRef(0);
  const saveQueue = useRef(Promise.resolve());
  const [detail, setDetail] = useState(media);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [saveStatus, setSaveStatus] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [rating, setRating] = useState('');
  const [reload, setReload] = useState(0);

  const save = (keepalive = false) => {
    if (!session.current || completed.current || !video.current) return Promise.resolve();
    const data = { session_id: session.current, sequence: sequence.current++,
      position_seconds: video.current.currentTime };
    lastSave.current = Date.now();
    saveQueue.current = saveQueue.current.catch(() => {}).then(() =>
      post('/playback/update', data, { keepalive }).then(() => setSaveStatus('Progress saved'))
        .catch(e => { setSaveStatus('Progress not saved — check your connection'); throw e; }));
    return saveQueue.current;
  };

  useEffect(() => {
    let cancelled = false;
    document.body.style.overflow = 'hidden';
    let timer;
    setReady(false); setError('');
    session.current = null;
    const open = async () => {
      try {
        const data = await api('/catalog/' + media.id);
        if (cancelled) return;
        setDetail(data);
        if (['failed', 'cancelled'].includes(data.playback_status)) {
          setError(data.prepare_error || 'Video preparation stopped. You can retry below.');
          return;
        }
        if (!data.available && data.playback_status === 'ready') {
          setError('The video file is missing or unavailable. Check the source or prepare it again.');
          return;
        }
        const playback = await post('/playback/start', { media_id: media.id });
        if (cancelled) return;
        setRating(data.rating || '');
        session.current = playback.session_id;
        sequence.current = 0; completed.current = false;
        setPosition(playback.position_seconds);
        setReady(true);
      } catch (e) { if (!cancelled) setError(e.message); }
    };
    open();
    const hide = () => { if (document.visibilityState === 'hidden') save(true).catch(() => {}); };
    const leave = () => { save(true).catch(() => {}); };
    document.addEventListener('visibilitychange', hide);
    window.addEventListener('pagehide', leave);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.body.style.overflow = '';
      document.removeEventListener('visibilitychange', hide);
      window.removeEventListener('pagehide', leave);
    };
  }, [media.id, reload]);

  useEffect(() => {
    if (!video.current || !ready) return;
    if (isPlaying) video.current.play().catch(e => { setError(e.message); setIsPlaying(false); });
    else video.current.pause();
  }, [isPlaying, ready]);

  const close = async () => {
    video.current?.pause();
    try { await save(); } catch (_) { return; }
    onClose();
  };
  const finish = async () => {
    if (!session.current || completed.current) return;
    completed.current = true;
    setIsPlaying(false);
    try {
      await saveQueue.current.catch(() => {});
      await post('/playback/complete', { session_id: session.current });
      setSaveStatus('Completed · added to watch history');
    } catch (e) { completed.current = false; setError(e.message); }
  };
  const retry = async () => {
    try {
      video.current?.pause();
      await save().catch(() => {});
      await post('/catalog/' + media.id + '/prepare', { force_transcode: ready });
      setIsPlaying(false);
      setReload(value => value + 1);
    } catch (e) { setError(e.message); }
  };
  const cancelPreparation = async () => {
    try {
      await post('/catalog/' + media.id + '/cancel', {});
      setReload(value => value + 1);
    } catch (e) { setError(e.message); }
  };
  const remove = async () => {
    try {
      await api('/catalog/' + media.id, { method: 'DELETE' });
      completed.current = true;
      onDelete(); onClose();
    } catch (e) { setError(e.message); }
  };
  const rate = async value => {
    setRating(value);
    if (!value) return;
    try { await post('/ratings', { media_id: media.id, rating: Number(value) }); }
    catch (e) { setError(e.message); }
  };
  return <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    className="fixed inset-0 z-[10000] bg-black/85 flex items-center justify-center p-4"
    role="dialog" aria-modal="true" aria-label={detail.title}>
    <motion.div {...sheetMotion} className="relative w-full max-w-4xl bg-canvas rounded-3xl p-5 md:p-8 max-h-[90vh] overflow-y-auto border border-white/15">
      <div className="flex items-center justify-between gap-4 mb-4">
        <h2 className="text-2xl text-white font-bold">{detail.title}</h2>
        <button aria-label="Close player" onClick={close} className="p-2 rounded-full bg-white/10"><X /></button>
      </div>
      <MovieDetails mediaId={media.id} user={user} onUpdate={setDetail} />
      {ready && <video ref={video} controls playsInline preload="metadata"
        className="w-full rounded-xl bg-black max-h-[55vh]"
        src={API_BASE_URL + '/media/' + media.id + '/stream'}
        onLoadedMetadata={() => {
          video.current.currentTime = Math.min(position, Math.max(0, video.current.duration - 0.25));
        }}
        onPlay={async () => {
          setIsPlaying(true);
          if (completed.current) {
            try {
              const next = await post('/playback/start', { media_id: media.id });
              session.current = next.session_id;
              sequence.current = 0;
              completed.current = false;
              setSaveStatus('');
            } catch (e) { video.current.pause(); setError(e.message); }
          }
        }} onPause={() => {
          setIsPlaying(false); save().catch(() => {});
        }}
        onTimeUpdate={() => {
          setPosition(video.current.currentTime);
          if (Date.now() - lastSave.current >= 10000) save().catch(() => {});
        }}
        onSeeked={() => save().catch(() => {})}
        onEnded={finish}
        onError={() => setError('Your browser could not play this video. Prepare a compatible copy using the button below.')}
      />}
      {!ready && !error && <div className="py-10 space-y-4" role="status">
        <p className="text-white/80">{detail.playback_status === 'pending' ? 'Queued for preparation…' :
          detail.playback_status === 'preparing' ? 'Preparing the full video for playback…' : 'Opening video…'}</p>
        {['pending', 'preparing'].includes(detail.playback_status) && <>
          <progress className="w-full" value={detail.prepare_progress || 0} max="100" />
          <p className="text-sm text-white/60">{Math.floor(detail.prepare_progress || 0)}% · The whole video is being prepared. Large files can take a while. You can close this window and return later.</p>
          {user.is_admin && <button className="underline text-sm" onClick={cancelPreparation}>Cancel preparation</button>}
        </>}
      </div>}
      {error && <p role="alert" className="my-4 text-red-300">{error}</p>}
      <p aria-live="polite" className="text-sm text-accent-soft mt-3">{saveStatus}</p>
      {saveStatus.startsWith('Progress not saved') && <button onClick={onClose} className="text-sm underline mt-2">Close without saving</button>}
      <div className="flex flex-wrap items-center justify-between gap-4 mt-6">
        <label className="text-white/80">Your rating
          <select aria-label="Your rating" value={rating} onChange={e => rate(e.target.value)}
            className="ml-3 p-2 rounded-lg bg-elevated">
            <option value="">Not rated</option>
            {Array.from({ length: 10 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1} / 10</option>)}
          </select>
        </label>
        {user.is_admin && <button onClick={() => setDeleting(true)}
          className="flex gap-2 text-red-300 items-center"><Trash2 size={16} />Remove from library</button>}
      </div>
      {error && user.is_admin && <button onClick={retry} className="block mt-4 px-4 py-2 rounded-xl bg-accent-strong text-white">
        {ready ? 'Prepare compatible video' : 'Retry preparation'}
      </button>}
      {error && !ready && <button onClick={onClose} className="mt-4 underline text-white">Back to library</button>}
    </motion.div>
    <ConfirmModal isOpen={deleting} title="Remove video?" message="This removes the catalog entry and its viewing history. The video file stays on disk."
      confirmText="Remove" cancelText="Cancel" variant="destructive"
      onConfirm={() => { setDeleting(false); remove(); }} onCancel={() => setDeleting(false)} />
  </motion.div>;
}
