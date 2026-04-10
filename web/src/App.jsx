import React, { useMemo, useState } from 'react'
import { getUploadUrl, putToS3, getResults } from './api.js'

export default function App() {
  const [file, setFile] = useState(null)
  const [job, setJob] = useState(null)
  const [status, setStatus] = useState('')
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  const [isBusy, setIsBusy] = useState(false)

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : ''), [file])

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setResults([])

    if (!file) {
      setError('Choose an image first.')
      return
    }

    setIsBusy(true)
    setStatus('Requesting upload URL…')

    try {
      const { jobId, uploadUrl } = await getUploadUrl()
      setJob({ jobId })

      setStatus('Uploading…')
      await putToS3(uploadUrl, file)

      setStatus('Processing…')
      const start = Date.now()
      while (true) {
        const data = await getResults(jobId)
        if (data.status === 'DONE') {
          setResults(data.results || [])
          setStatus('DONE')
          break
        }
        if (data.status === 'ERROR') {
          setStatus('ERROR')
          setError('Processing failed.')
          break
        }
        if (Date.now() - start > 60_000) {
          setStatus('TIMEOUT')
          setError('Timed out waiting for results.')
          break
        }
        await new Promise((r) => setTimeout(r, 1500))
      }
    } catch (err) {
      setError(err?.message || 'Something went wrong')
      setStatus('')
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', padding: 16, fontFamily: 'system-ui' }}>
      <h1 style={{ marginBottom: 8 }}>TrendLens</h1>
      <p style={{ marginTop: 0 }}>Upload a clothing photo to find 5 similar items.</p>

      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <input
          type="file"
          accept="image/*"
          disabled={isBusy}
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        {previewUrl ? (
          <img
            src={previewUrl}
            alt="preview"
            style={{ width: 240, height: 240, objectFit: 'cover' }}
          />
        ) : null}

        <button type="submit" disabled={isBusy} style={{ width: 220, padding: '10px 12px' }}>
          {isBusy ? 'Working…' : 'Find Similar Items'}
        </button>
      </form>

      {status ? <p style={{ marginTop: 16 }}>Status: {status}</p> : null}
      {error ? <p style={{ marginTop: 8 }}>{error}</p> : null}

      {results?.length ? (
        <div style={{ marginTop: 20 }}>
          <h2 style={{ marginBottom: 8 }}>Top 5</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
            {results.slice(0, 5).map((item) => (
              <div key={item.product_id} style={{ padding: 10 }}>
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={item.title || item.product_id}
                    style={{ width: '100%', height: 180, objectFit: 'cover' }}
                  />
                ) : null}
                <div style={{ marginTop: 8, fontWeight: 600 }}>{item.title || item.product_id}</div>
                {item.price ? <div>${item.price}</div> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {job?.jobId ? <p style={{ marginTop: 16 }}>Job: {job.jobId}</p> : null}
    </div>
  )
}
