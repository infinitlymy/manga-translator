import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Upload as UploadIcon, X, ImagePlus } from 'lucide-react'

interface UploadingFile {
  file: File
  id: string
  progress: number
  status: 'pending' | 'uploading' | 'done' | 'error'
  error?: string
}

export function Upload() {
  const queryClient = useQueryClient()
  const [files, setFiles] = useState<UploadingFile[]>([])
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return
    const newFiles: UploadingFile[] = Array.from(fileList)
      .filter((f) => f.type.startsWith('image/'))
      .map((file) => ({
        file,
        id: Math.random().toString(36).slice(2),
        progress: 0,
        status: 'pending',
      }))
    setFiles((prev) => [...prev, ...newFiles])
    newFiles.forEach(uploadFile)
  }, [])

  const uploadFile = async (uf: UploadingFile) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === uf.id ? { ...f, status: 'uploading' as const } : f))
    )
    try {
      const formData = new FormData()
      formData.append('file', uf.file)
      await api.post('/uploads', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          const progress = e.total ? Math.round((e.loaded / e.total) * 100) : 0
          setFiles((prev) =>
            prev.map((f) => (f.id === uf.id ? { ...f, progress } : f))
          )
        },
      })
      setFiles((prev) =>
        prev.map((f) => (f.id === uf.id ? { ...f, status: 'done' as const, progress: 100 } : f))
      )
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    } catch (err: any) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uf.id ? { ...f, status: 'error' as const, error: err.message } : f
        )
      )
    }
  }

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return
    const files: File[] = []
    for (const item of items) {
      if (item.kind === 'file') {
        const file = item.getAsFile()
        if (file && file.type.startsWith('image/')) files.push(file)
      }
    }
    if (files.length) {
      const dataTransfer = new DataTransfer()
      files.forEach((f) => dataTransfer.items.add(f))
      handleFiles(dataTransfer.files)
    }
  }

  return (
    <div className="space-y-6" onPaste={handlePaste}>
      <h1 className="text-2xl font-bold">Upload Images</h1>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
          dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        }`}
      >
        <ImagePlus className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <p className="text-gray-600 mb-2">Drag & drop images here, paste from clipboard, or click to browse</p>
        <input
          type="file"
          multiple
          accept="image/*"
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
          id="file-input"
        />
        <label
          htmlFor="file-input"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer"
        >
          <UploadIcon className="w-4 h-4" />
          Browse Files
        </label>
      </div>

      {files.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm divide-y">
          {files.map((f) => (
            <div key={f.id} className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 bg-gray-100 rounded overflow-hidden flex-shrink-0">
                <img
                  src={URL.createObjectURL(f.file)}
                  alt=""
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{f.file.name}</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        f.status === 'error' ? 'bg-red-500' : f.status === 'done' ? 'bg-green-500' : 'bg-blue-600'
                      }`}
                      style={{ width: `${f.progress}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-12 text-right">{f.progress}%</span>
                </div>
                {f.error && <p className="text-xs text-red-600 mt-1">{f.error}</p>}
              </div>
              <button onClick={() => removeFile(f.id)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
