const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8080'

export async function getUploadUrl() {
  const res = await fetch(`${API_BASE}/upload-url`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to get upload URL')
  return res.json()
}

export async function putToS3(uploadUrl, file) {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type || 'application/octet-stream'
    },
    body: file
  })
  if (!res.ok) throw new Error('Upload failed')
}

export async function getResults(jobId) {
  const res = await fetch(`${API_BASE}/results/${encodeURIComponent(jobId)}`)
  if (!res.ok) throw new Error('Failed to fetch results')
  return res.json()
}
