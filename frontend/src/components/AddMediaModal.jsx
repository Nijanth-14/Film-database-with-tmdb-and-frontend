import { sheetMotion } from '../motion';
import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { api, post } from '../api';
import FolderImport from './FolderImport';

export default function AddMediaModal({ isOpen, onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [folderMode, setFolderMode] = useState(false);
  const [path, setPath] = useState('');
  const [fetchMetadata, setFetchMetadata] = useState(true);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [inspecting, setInspecting] = useState(false);
  const [saving, setSaving] = useState(false);
  const request = useRef(0);
  const [files, setFiles] = useState([]);
  const [pickerError, setPickerError] = useState('');
  useEffect(() => {
    api('/import/files').then(setFiles).catch(e => setPickerError(e.message));
  }, []);
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);
  useEffect(() => {
    const id = ++request.current;
    setInfo(null); setError(''); setInspecting(false);
    if (folderMode || !path.trim()) return;
    const timer = setTimeout(async () => {
      setInspecting(true);
      try {
        const result = await post('/import/inspect', { path });
        if (id === request.current) {
          if (result.kind === 'folder') setFolderMode(true);
          else setInfo(result);
        }
      } catch (e) { if (id === request.current) setError(e.message); }
      finally { if (id === request.current) setInspecting(false); }
    }, 700);
    return () => { clearTimeout(timer); ++request.current; };
  }, [path, folderMode]);
  const submit = async e => {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      const detected = await post('/import/inspect', { path });
      if (detected.kind === 'folder') { setFolderMode(true); return; }
      await post('/catalog', { title, path, fetch_metadata: fetchMetadata });
      onSuccess(); onClose();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };
  if (!isOpen) return null;
  if (folderMode) return <FolderImport initialFolder={path} initialMetadata={fetchMetadata} onBack={() => { setPath(''); setFolderMode(false); }} onClose={onClose} onSuccess={onSuccess} />;
  return <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/70 backdrop-blur-md"
    role="dialog" aria-modal="true" aria-label="Add media">
    <motion.form {...sheetMotion} onSubmit={submit} className="w-full max-w-lg glass rounded-3xl p-8 space-y-5 max-h-[90vh] overflow-y-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-white">Add media</h2>
        <button type="button" aria-label="Close import" disabled={saving} onClick={onClose} className="p-2"><X /></button>
      </div>
      <button type="button" onClick={() => setFolderMode(true)} className="w-full rounded-xl border border-accent/40 bg-accent/10 p-3 text-blue-100 font-medium">Import a folder with seasons and episodes</button>
      <label className="block text-white/80">Choose a video from your library
        <select aria-label="Choose video" value={files.some(f => f.path === path) ? path : ''}
          onChange={e => setPath(e.target.value)}
          className="mt-2 w-full rounded-xl bg-surface border border-white/20 p-3 text-white">
          <option value="">Select a video…</option>
          {files.map(file => <option key={file.path} value={file.path}>{file.name}</option>)}
        </select>
      </label>
      {pickerError && <p role="alert" className="text-red-200">{pickerError}</p>}
      <label className="block text-white/80">Or paste a video or folder path
        <input required autoFocus value={path} onChange={e => setPath(e.target.value)}
          placeholder="Paste a movie, episode, or series folder path"
          className="mt-2 w-full bg-black/40 border border-white/20 rounded-xl p-3 text-white" />
      </label>
      <label className="block text-white/80">Title <span className="text-white/50">(optional)</span>
        <input value={title} onChange={e => setTitle(e.target.value)} placeholder={info?.title || 'Detected from the filename'}
          className="mt-2 w-full bg-black/40 border border-white/20 rounded-xl p-3 text-white" />
      </label>
      {inspecting && <p role="status" className="text-accent-soft">Checking file or folder…</p>}
      {info && <div className="p-4 rounded-xl bg-accent/10 text-blue-100 space-y-1" role="status">
        <p className="font-medium">{info.title}</p>
        <p>{info.media_type === 'tv' ? 'Series' : 'Movie'}
          {info.season_number != null ? ' · Season ' + info.season_number : ''}
          {info.episode_number != null ? ' · Episode ' + info.episode_number : ''}
          {' · ' + Math.floor(info.duration_seconds / 60) + ' min ' + Math.floor(info.duration_seconds % 60) + ' sec'}
        </p>
        <p className="text-sm">{info.requires_preparation
          ? 'The full video will be prepared for playback. Progress appears in your library.'
          : 'Ready for direct playback.'}</p>
      </div>}
      <label className="flex gap-3 items-center text-white/70 text-sm">
        <input type="checkbox" checked={fetchMetadata} onChange={e => setFetchMetadata(e.target.checked)} />
        Look up artwork and details online
      </label>
      <p className="text-sm text-white/60">Movie or series and duration are detected automatically. MKV, MP4, WebM, MOV and AVI are supported. Your whole video is imported; the original stays unchanged.</p>
      {error && <p role="alert" className="p-3 rounded-xl bg-red-950/40 text-red-200">{error}</p>}
      <button disabled={saving || inspecting} className="w-full py-3 rounded-xl text-white bg-accent-strong disabled:opacity-50 font-semibold">
        {saving ? 'Importing…' : 'Add to library'}
      </button>
    </motion.form>
  </motion.div>;
}
