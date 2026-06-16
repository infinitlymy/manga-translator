import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { ArrowLeft, Play, Trash2, Settings, BookOpen, Plus, X } from 'lucide-react'

const LANGUAGES = [
  { value: 'ENG', label: 'English' },
  { value: 'CHS', label: 'Chinese (Simplified)' },
  { value: 'CHT', label: 'Chinese (Traditional)' },
  { value: 'JPN', label: 'Japanese' },
  { value: 'KOR', label: 'Korean' },
  { value: 'FRA', label: 'French' },
  { value: 'DEU', label: 'German' },
  { value: 'RUS', label: 'Russian' },
  { value: 'SPA', label: 'Spanish' },
  { value: 'ITA', label: 'Italian' },
  { value: 'THA', label: 'Thai' },
  { value: 'IND', label: 'Indonesian' },
  { value: 'VIE', label: 'Vietnamese' },
  { value: 'ARA', label: 'Arabic' },
  { value: 'POR', label: 'Portuguese' },
  { value: 'TUR', label: 'Turkish' },
  { value: 'POL', label: 'Polish' },
  { value: 'UKR', label: 'Ukrainian' },
]

const TRANSLATORS = [
  'sugoi', 'youdao', 'baidu', 'google', 'deepl', 'papago',
  'gpt3.5', 'gpt4', 'gpt4-turbo', 'gpt4o', 'gpt4o-mini',
  'sakura-009', 'sakura-010', 'qwen2', 'qwen2-7b-instruct',
  'qwen2-gptq', 'qwen2.5-coder-awq', 'yi-34b-chat-8bit',
  'sakura-13b-qwen2.5-awq', 'gemini-2.0-flash',
]

const DETECTORS = ['default', 'ctd', 'craft', 'db', 'db_panet', 'east', 'panet', 'craft-prod']
const INPAINTERS = ['default', 'lama', 'lama_large', 'sd', 'sd_laion', 'zits', 'manga', 'mv']
const OCR = ['default', 'ocr48px', 'ocr32px', 'mocr', 'star']
const RENDERERS = ['default', 'manga2eng', 'render_demo']

export function CollectionDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showJobForm, setShowJobForm] = useState(false)
  const [jobName, setJobName] = useState('')
  const [targetLang, setTargetLang] = useState('ENG')
  const [activePanel, setActivePanel] = useState<'assets' | 'settings' | 'dictionary'>('assets')

  const { data: collection } = useQuery({
    queryKey: ['collection', id],
    queryFn: async () => {
      const res = await api.get(`/collections/${id}`)
      return res.data
    },
    enabled: !!id,
  })

  const { data: assets } = useQuery({
    queryKey: ['collection-assets', id],
    queryFn: async () => {
      const res = await api.get(`/collections/${id}/assets`)
      return res.data
    },
    enabled: !!id,
  })

  const createJob = useMutation({
    mutationFn: () =>
      api.post('/jobs/', {
        collection_id: id,
        name: jobName || undefined,
        config_snapshot: { translator: { target_lang: targetLang } },
      }),
    onSuccess: () => {
      setShowJobForm(false)
      setJobName('')
      navigate('/jobs')
    },
  })

  const deleteAsset = useMutation({
    mutationFn: (assetId: string) => api.delete(`/uploads/assets/${assetId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['collection-assets', id] }),
  })

  if (!collection) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/collections')} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold">{collection.name}</h1>
          {(collection.series || collection.artist) && (
            <p className="text-sm text-gray-500">
              {collection.series && <span className="mr-3">Series: {collection.series}</span>}
              {collection.artist && <span>Artist: {collection.artist}</span>}
            </p>
          )}
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setShowJobForm(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <Play className="w-4 h-4" />
          Translate Collection
        </button>
        <button
          onClick={() => setActivePanel('assets')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-md border ${activePanel === 'assets' ? 'bg-gray-100 border-gray-300' : 'hover:bg-gray-50'}`}
        >
          Assets ({assets?.length || 0})
        </button>
        <button
          onClick={() => setActivePanel('settings')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-md border ${activePanel === 'settings' ? 'bg-gray-100 border-gray-300' : 'hover:bg-gray-50'}`}
        >
          <Settings className="w-4 h-4" />
          Translation Settings
        </button>
        <button
          onClick={() => setActivePanel('dictionary')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-md border ${activePanel === 'dictionary' ? 'bg-gray-100 border-gray-300' : 'hover:bg-gray-50'}`}
        >
          <BookOpen className="w-4 h-4" />
          Dictionary
        </button>
      </div>

      {showJobForm && (
        <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
          <h3 className="font-semibold">Start Translation Job</h3>
          <input
            placeholder="Job name (optional)"
            value={jobName}
            onChange={(e) => setJobName(e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              onClick={() => createJob.mutate()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Start
            </button>
            <button onClick={() => setShowJobForm(false)} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {activePanel === 'assets' && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {assets?.map((asset: any) => (
            <div key={asset.id} className="bg-white rounded-lg shadow-sm overflow-hidden group">
              <div className="aspect-square bg-gray-100 relative">
                <img
                  src={`/storage/${asset.stored_path}`}
                  alt={asset.original_name}
                  className="w-full h-full object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).src = '' }}
                />
                <button
                  onClick={() => deleteAsset.mutate(asset.id)}
                  className="absolute top-2 right-2 p-1 bg-white/80 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              </div>
              <div className="p-2">
                <p className="text-xs truncate">{asset.original_name}</p>
                <p className="text-xs text-gray-400">{Math.round(asset.size / 1024)} KB</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {activePanel === 'settings' && id && <TranslationSettings collectionId={id} collection={collection} />}
      {activePanel === 'dictionary' && id && <DictionaryPanel collectionId={id} />}
    </div>
  )
}

function TranslationSettings({ collectionId, collection }: { collectionId: string; collection: any }) {
  const queryClient = useQueryClient()

  const { data: config } = useQuery({
    queryKey: ['collection-config', collectionId],
    queryFn: async () => {
      const res = await api.get(`/collections/${collectionId}/config`)
      return res.data as Record<string, any>
    },
  })

  const saveConfig = useMutation({
    mutationFn: (data: any) => api.put(`/collections/${collectionId}/config`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['collection-config', collectionId] }),
  })

  const updateCollection = useMutation({
    mutationFn: (data: any) => api.put(`/collections/${collectionId}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['collection', collectionId] }),
  })

  const [form, setForm] = useState<Record<string, any>>({})
  const [series, setSeries] = useState(collection?.series || '')
  const [artist, setArtist] = useState(collection?.artist || '')

  useEffect(() => {
    if (config) setForm(config)
  }, [config])

  const updateField = (section: string, key: string, value: any) => {
    setForm((prev) => ({
      ...prev,
      [section]: { ...(prev[section] || {}), [key]: value },
    }))
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 space-y-6">
      <h3 className="font-semibold text-lg">Collection Translation Settings</h3>
      <p className="text-sm text-gray-500">These settings override global defaults for this collection.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Series</label>
          <input
            value={series}
            onChange={(e) => setSeries(e.target.value)}
            placeholder="e.g. Naruto"
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Artist</label>
          <input
            value={artist}
            onChange={(e) => setArtist(e.target.value)}
            placeholder="e.g. Kishimoto"
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
      </div>

      <button
        onClick={() => updateCollection.mutate({ series, artist })}
        className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-800"
      >
        Save Taxonomy
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Target Language</label>
          <select
            value={form.translator?.target_lang || 'ENG'}
            onChange={(e) => updateField('translator', 'target_lang', e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Translator Engine</label>
          <select
            value={form.translator?.translator || 'sugoi'}
            onChange={(e) => updateField('translator', 'translator', e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            {TRANSLATORS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Detector</label>
          <select
            value={form.detector?.detector || 'default'}
            onChange={(e) => updateField('detector', 'detector', e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            {DETECTORS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Inpainter</label>
          <select
            value={form.inpainter?.inpainter || 'lama_large'}
            onChange={(e) => updateField('inpainter', 'inpainter', e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            {INPAINTERS.map((i) => (
              <option key={i} value={i}>{i}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">OCR</label>
          <select
            value={form.ocr?.ocr || 'ocr48px'}
            onChange={(e) => updateField('ocr', 'ocr', e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            {OCR.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Renderer</label>
          <select
            value={form.render?.renderer || 'default'}
            onChange={(e) => updateField('render', 'renderer', e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            {RENDERERS.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={() => saveConfig.mutate(form)}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
      >
        Save Settings
      </button>
    </div>
  )
}

function DictionaryPanel({ collectionId }: { collectionId: string }) {
  const queryClient = useQueryClient()
  const [newTerm, setNewTerm] = useState({ pattern: '', replacement: '', phase: 'post', note: '' })

  const { data: terms } = useQuery({
    queryKey: ['dictionary', collectionId],
    queryFn: async () => {
      const res = await api.get('/dictionaries/', { params: { collection_id: collectionId } })
      return res.data as any[]
    },
  })

  const createTerm = useMutation({
    mutationFn: () =>
      api.post('/dictionaries/', {
        collection_id: collectionId,
        ...newTerm,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dictionary', collectionId] })
      setNewTerm({ pattern: '', replacement: '', phase: 'post', note: '' })
    },
  })

  const deleteTerm = useMutation({
    mutationFn: (termId: string) => api.delete(`/dictionaries/${termId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dictionary', collectionId] }),
  })

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 space-y-6">
      <h3 className="font-semibold text-lg">Dictionary / Replacement Terms</h3>
      <p className="text-sm text-gray-500">
        Pre-translation terms are replaced <b>before</b> sending to the translator.
        Post-translation terms are replaced <b>after</b> translation.
      </p>

      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <h4 className="text-sm font-medium">Add New Term</h4>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            placeholder="Pattern to match"
            value={newTerm.pattern}
            onChange={(e) => setNewTerm((p) => ({ ...p, pattern: e.target.value }))}
            className="px-3 py-2 border rounded-md"
          />
          <input
            placeholder="Replacement"
            value={newTerm.replacement}
            onChange={(e) => setNewTerm((p) => ({ ...p, replacement: e.target.value }))}
            className="px-3 py-2 border rounded-md"
          />
          <select
            value={newTerm.phase}
            onChange={(e) => setNewTerm((p) => ({ ...p, phase: e.target.value }))}
            className="px-3 py-2 border rounded-md"
          >
            <option value="pre">Pre-translation</option>
            <option value="post">Post-translation</option>
          </select>
          <button
            onClick={() => createTerm.mutate()}
            disabled={!newTerm.pattern}
            className="inline-flex items-center justify-center gap-1 px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>
        <input
          placeholder="Note (optional)"
          value={newTerm.note}
          onChange={(e) => setNewTerm((p) => ({ ...p, note: e.target.value }))}
          className="w-full px-3 py-2 border rounded-md text-sm"
        />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-3 py-2">Phase</th>
              <th className="px-3 py-2">Pattern</th>
              <th className="px-3 py-2">Replacement</th>
              <th className="px-3 py-2">Note</th>
              <th className="px-3 py-2">Usage</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {terms?.map((term: any) => (
              <tr key={term.id}>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${term.phase === 'pre' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
                    {term.phase}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-xs">{term.pattern}</td>
                <td className="px-3 py-2 font-mono text-xs">{term.replacement}</td>
                <td className="px-3 py-2 text-gray-500 text-xs">{term.note || '-'}</td>
                <td className="px-3 py-2 text-gray-500 text-xs">{term.usage_count}</td>
                <td className="px-3 py-2">
                  <button
                    onClick={() => deleteTerm.mutate(term.id)}
                    className="p-1 hover:bg-red-50 text-red-600 rounded"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!terms || terms.length === 0) && (
          <div className="p-4 text-center text-gray-400 text-sm">No terms yet.</div>
        )}
      </div>
    </div>
  )
}
