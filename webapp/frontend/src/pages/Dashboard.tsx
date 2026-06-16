import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { FolderOpen, Image, ListTodo, Settings } from 'lucide-react'

function StatCard({ label, value, icon: Icon }: { label: string; value: number; icon: React.ElementType }) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-6 flex items-center gap-4">
      <div className="p-3 bg-blue-50 rounded-lg">
        <Icon className="w-6 h-6 text-blue-600" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  )
}

export function Dashboard() {
  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: async () => {
      const res = await api.get('/collections')
      return res.data
    },
  })

  const { data: assets } = useQuery({
    queryKey: ['assets'],
    queryFn: async () => {
      const res = await api.get('/uploads/assets')
      return res.data
    },
  })

  const { data: jobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const res = await api.get('/jobs')
      return res.data
    },
  })

  const { data: results } = useQuery({
    queryKey: ['results'],
    queryFn: async () => {
      const res = await api.get('/results')
      return res.data
    },
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Collections" value={collections?.length || 0} icon={FolderOpen} />
        <StatCard label="Assets" value={assets?.length || 0} icon={Image} />
        <StatCard label="Jobs" value={jobs?.length || 0} icon={ListTodo} />
        <StatCard label="Results" value={results?.length || 0} icon={Settings} />
      </div>
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Recent Jobs</h2>
        {jobs && jobs.length > 0 ? (
          <div className="divide-y">
            {jobs.slice(0, 5).map((job: any) => (
              <div key={job.id} className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium">{job.name}</p>
                  <p className="text-sm text-gray-500">{job.status}</p>
                </div>
                <div className="w-32">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 transition-all"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No jobs yet.</p>
        )}
      </div>
    </div>
  )
}
