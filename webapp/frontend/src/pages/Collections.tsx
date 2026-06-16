import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { FolderOpen, Plus, Trash2 } from 'lucide-react'

export function Collections() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [series, setSeries] = useState('')
  const [artist, setArtist] = useState('')
  const [showForm, setShowForm] = useState(false)

  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: async () => {
      const res = await api.get('/collections/')
      return res.data
    },
  })

  const create = useMutation({
    mutationFn: (data: { name: string; description: string; series?: string; artist?: string }) => api.post('/collections/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] })
      setName('')
      setDesc('')
      setSeries('')
      setArtist('')
      setShowForm(false)
    },
  })

  const del = useMutation({
    mutationFn: (id: string) => api.delete(`/collections/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['collections'] }),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Collections</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          New Collection
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            create.mutate({ name, description: desc, series, artist })
          }}
          className="bg-white rounded-lg shadow-sm p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Series</label>
              <input
                value={series}
                onChange={(e) => setSeries(e.target.value)}
                placeholder="e.g. Naruto"
                className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Artist</label>
              <input
                value={artist}
                onChange={(e) => setArtist(e.target.value)}
                placeholder="e.g. Kishimoto"
                className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
              Create
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {collections?.map((c: any) => (
          <div key={c.id} className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-4">
              <FolderOpen className="w-8 h-8 text-blue-600" />
              <button
                onClick={() => del.mutate(c.id)}
                className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <Link to={`/collections/${c.id}`} className="block">
              <h3 className="text-lg font-semibold mb-1 hover:text-blue-600">{c.name}</h3>
            </Link>
            {c.description && <p className="text-sm text-gray-500 mb-1">{c.description}</p>}
            {(c.series || c.artist) && (
              <p className="text-xs text-gray-500 mb-1">
                {c.series && <span className="mr-2">Series: {c.series}</span>}
                {c.artist && <span>Artist: {c.artist}</span>}
              </p>
            )}
            <p className="text-xs text-gray-400">{new Date(c.created_at).toLocaleDateString()}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
