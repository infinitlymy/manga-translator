import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Download, Eye } from 'lucide-react'

export function Gallery() {
  const [selected, setSelected] = useState<string[]>([])
  const [previewId, setPreviewId] = useState<string | null>(null)

  const { data: results } = useQuery({
    queryKey: ['results'],
    queryFn: async () => {
      const res = await api.get('/results')
      return res.data
    },
  })

  const toggleSelect = (id: string) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const handleExport = async () => {
    if (selected.length === 0) return
    const res = await api.post('/export/zip', { result_ids: selected }, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'export.zip')
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Gallery</h1>
        {selected.length > 0 && (
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Download className="w-4 h-4" />
            Export {selected.length} selected
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {results?.map((result: any) => (
          <div
            key={result.id}
            className={`bg-white rounded-lg shadow-sm overflow-hidden cursor-pointer ring-2 ring-transparent ${
              selected.includes(result.id) ? 'ring-blue-500' : ''
            }`}
            onClick={() => toggleSelect(result.id)}
          >
            <div className="aspect-square bg-gray-100 relative group">
              <img
                src={`/api/results/${result.id}/image?thumb=true`}
                alt=""
                className="w-full h-full object-cover"
                loading="lazy"
              />
              <button
                onClick={(e) => { e.stopPropagation(); setPreviewId(result.id) }}
                className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/20 transition-colors"
              >
                <Eye className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
              <div className="absolute top-2 left-2">
                <input
                  type="checkbox"
                  checked={selected.includes(result.id)}
                  onChange={() => toggleSelect(result.id)}
                  className="w-4 h-4"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </div>
            <div className="p-2 text-xs text-gray-500">
              {new Date(result.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>

      {previewId && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setPreviewId(null)}
        >
          <img
            src={`/api/results/${previewId}/image`}
            alt=""
            className="max-w-full max-h-full rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}
