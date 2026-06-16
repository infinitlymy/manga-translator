import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { History, RotateCcw, Eye, X } from 'lucide-react'

const ACTION_COLORS: Record<string, string> = {
  create: 'bg-green-100 text-green-700',
  update: 'bg-blue-100 text-blue-700',
  delete: 'bg-red-100 text-red-700',
}

export function HistoryPage() {
  const queryClient = useQueryClient()
  const [filterTable, setFilterTable] = useState('')
  const [filterAction, setFilterAction] = useState('')
  const [selectedLog, setSelectedLog] = useState<any>(null)

  const { data: logs } = useQuery({
    queryKey: ['audit-log', filterTable, filterAction],
    queryFn: async () => {
      const res = await api.get('/audit-log/', {
        params: {
          ...(filterTable && { table_name: filterTable }),
          ...(filterAction && { action: filterAction }),
          limit: 200,
        },
      })
      return res.data as any[]
    },
  })

  const revert = useMutation({
    mutationFn: (logId: string) => api.post(`/audit-log/${logId}/revert`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit-log'] })
      setSelectedLog(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <History className="w-6 h-6" />
          History / Audit Log
        </h1>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select
          value={filterTable}
          onChange={(e) => setFilterTable(e.target.value)}
          className="px-3 py-2 border rounded-md text-sm"
        >
          <option value="">All Tables</option>
          <option value="collections">Collections</option>
          <option value="dictionaries">Dictionaries</option>
          <option value="assets">Assets</option>
          <option value="jobs">Jobs</option>
          <option value="settings">Settings</option>
        </select>

        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="px-3 py-2 border rounded-md text-sm"
        >
          <option value="">All Actions</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
        </select>
      </div>

      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Table</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Record</th>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Reverted</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {logs?.map((log: any) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 font-medium">{log.table_name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${ACTION_COLORS[log.action] || 'bg-gray-100'}`}>
                    {log.action}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{log.record_id}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{log.user_id?.slice(0, 8) || '-'}</td>
                <td className="px-4 py-3">
                  {log.reverted_at ? (
                    <span className="text-xs text-orange-600">Yes</span>
                  ) : (
                    <span className="text-xs text-gray-400">No</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="p-1 hover:bg-blue-50 text-blue-600 rounded"
                      title="View diff"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    {log.action === 'update' && !log.reverted_at && (
                      <button
                        onClick={() => revert.mutate(log.id)}
                        className="p-1 hover:bg-orange-50 text-orange-600 rounded"
                        title="Revert"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!logs || logs.length === 0) && (
          <div className="p-8 text-center text-gray-400 text-sm">No history entries yet.</div>
        )}
      </div>

      {selectedLog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-[80vh] overflow-auto m-4">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold">Change Details</h3>
              <button onClick={() => setSelectedLog(null)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><b>Table:</b> {selectedLog.table_name}</div>
                <div><b>Action:</b> {selectedLog.action}</div>
                <div><b>Record ID:</b> {selectedLog.record_id}</div>
                <div><b>Time:</b> {new Date(selectedLog.created_at).toLocaleString()}</div>
              </div>

              {selectedLog.old_data && (
                <div>
                  <h4 className="text-sm font-medium text-red-600 mb-1">Before</h4>
                  <pre className="bg-gray-50 rounded-md p-3 text-xs overflow-auto">
                    {JSON.stringify(selectedLog.old_data, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.new_data && (
                <div>
                  <h4 className="text-sm font-medium text-green-600 mb-1">After</h4>
                  <pre className="bg-gray-50 rounded-md p-3 text-xs overflow-auto">
                    {JSON.stringify(selectedLog.new_data, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.reverted_at && (
                <div className="bg-orange-50 text-orange-700 text-sm p-3 rounded-md">
                  Reverted at {new Date(selectedLog.reverted_at).toLocaleString()}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
