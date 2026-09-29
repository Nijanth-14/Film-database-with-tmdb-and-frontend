import { sheetMotion } from '../motion';
import { motion } from 'framer-motion';
import React, { useState } from 'react';
import { X } from 'lucide-react';
import { post } from '../api';

export default function FolderImport({ onBack, onClose, onSuccess, initialFolder = '', initialMetadata = true }) {
  const [folder, setFolder] = useState(initialFolder);
  const [items, setItems] = useState([]);
  const [metadata, setMetadata] = useState(initialMetadata);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState('');
  const [summary, setSummary] = useState(null);
  const scan = async e => {
    e.preventDefault(); setBusy(true); setError(''); setSummary(null); setProgress('Scanning folders…');
    try {
      const result = await post('/import/folder/scan', { path: folder });
      setItems(result.items);
      if (!result.items.length) setError('No supported video files found in this folder.');
    } catch (e) { setError(e.message); setItems([]); }
    finally { setBusy(false); setProgress(''); }
  };
  const add = async () => {
    setBusy(true); setError(''); setSummary(null);
    let added = 0, skipped = 0;
    const failed = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      setProgress('Importing ' + (i + 1) + ' of ' + items.length + ': ' + item.filename);
      try { await post('/catalog', { path: item.path, fetch_metadata: metadata }); added++; }
      catch (e) {
        if (e.message.includes('already in the catalog')) skipped++;
        else failed.push(item.filename + ': ' + e.message);
      }
    }
    setSummary({ added, skipped, failed }); setBusy(false); setProgress('');
    if (added) onSuccess();
  };
  return <div className="fixed inset-0 z-[10000] bg-black/75 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Import folder">
    <motion.section {...sheetMotion} className="w-full max-w-2xl glass rounded-3xl p-6 max-h-[90vh] overflow-y-auto space-y-5">
      <header className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Import a folder</h2>
        <button aria-label="Close folder import" disabled={busy} onClick={onClose}><X /></button>
      </header>
      <p className="text-white/70 text-sm">Season subfolders are included. Episodes are grouped into one series card. Rescanning skips files already in your library.</p>
      <form onSubmit={scan} className="space-y-3">
        <label className="block text-white">Folder path
          <input required disabled={busy} value={folder}
            onChange={e => { setFolder(e.target.value); setItems([]); setSummary(null); }}
            placeholder="Full path to a series or media folder"
            className="mt-2 w-full rounded-xl border border-white/20 bg-black/40 p-3" />
        </label>
        <button disabled={busy} className="bg-accent-strong rounded-lg px-4 py-2 text-white">Scan folder</button>
      </form>
      {items.length > 0 && <>
        <p className="text-white">{items.length} videos found</p>
        <div className="max-h-48 overflow-y-auto text-sm text-white/70 space-y-2">
          {items.map(item => <p key={item.path}>{item.title}
            {item.media_type === 'tv' ? ' · S' + (item.season_number ?? 1) + ' E' + (item.episode_number ?? '?') : ' · Movie'}
            <span className="block text-xs text-white/40 truncate">{item.filename}</span>
          </p>)}
        </div>
        <label className="flex items-center gap-3 text-white/70 text-sm">
          <input type="checkbox" checked={metadata} disabled={busy} onChange={e => setMetadata(e.target.checked)} />Look up artwork and details
        </label>
        <button disabled={busy} onClick={add} className="w-full bg-accent-strong text-white rounded-xl p-3 disabled:opacity-50">
          {busy ? 'Working…' : 'Import ' + items.length + ' videos'}
        </button>
      </>}
      {progress && <p role="status" className="text-accent-soft break-words">{progress}</p>}
      {error && <p role="alert" className="text-red-200">{error}</p>}
      {summary && <div role="status" className="text-white/80 space-y-2">
        <p>{summary.added} imported · {summary.skipped} already present · {summary.failed.length} failed</p>
        {summary.failed.map((failure,i) => <p key={i} className="text-red-200 text-xs">{failure}</p>)}
      </div>}
      <button disabled={busy} onClick={onBack} className="text-sm text-accent-soft underline">Back to single-file import</button>
    </motion.section>
  </div>;
}
