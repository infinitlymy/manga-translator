import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Save } from 'lucide-react'

interface SettingItem {
  key: string
  value: string
  type: 'text' | 'number'
  label: string
}

const settingDefs: SettingItem[] = [
  { key: 'default_detector', label: 'Default Detector', value: 'default', type: 'text' },
  { key: 'default_translator', label: 'Default Translator', value: 'youdao', type: 'text' },
  { key: 'default_inpainter', label: 'Default Inpainter', value: 'default', type: 'text' },
  { key: 'default_target_lang', label: 'Target Language', value: 'CHS', type: 'text' },
  { key: 'result_retention_days', label: 'Result Retention (days)', value: '30', type: 'number' },
]

export function Settings() {
  const queryClient = useQueryClient()
  const [values, setValues] = useState<Record<string, string>>({})

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await api.get('/settings')
      return res.data as Record<string, string | number>
    },
  })

  const updateBulk = useMutation({
    mutationFn: (data: Record<string, string | number>) => api.put('/settings/bulk', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  })

  const getValue = (key: string, defaultValue: string) => {
    if (values[key] !== undefined) return values[key]
    if (settings && settings[key] !== undefined) return String(settings[key])
    return defaultValue
  }

  const handleSave = () => {
    const payload: Record<string, string | number> = {}
    settingDefs.forEach((def) => {
      const val = values[def.key]
      if (val !== undefined) {
        payload[def.key] = def.type === 'number' ? Number(val) : val
      }
    })
    updateBulk.mutate(payload)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>
      <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
        {settingDefs.map((def) => (
          <div key={def.key}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{def.label}</label>
            <input
              type={def.type === 'number' ? 'number' : 'text'}
              value={getValue(def.key, def.value)}
              onChange={(e) => setValues((prev) => ({ ...prev, [def.key]: e.target.value }))}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}
        <button
          onClick={handleSave}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <Save className="w-4 h-4" />
          Save Settings
        </button>
      </div>
    </div>
  )
}
