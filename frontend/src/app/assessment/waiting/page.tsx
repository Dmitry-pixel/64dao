'use client'
import { useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

function WaitingContent() {
  const router = useRouter()
  const params = useSearchParams()
  const assessmentId = params.get('id')

  useEffect(() => {
    if (assessmentId) {
      router.replace('/report/' + assessmentId)
    } else {
      router.replace('/dashboard')
    }
  }, [assessmentId, router])

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)', fontSize: 14 }}>
      Загрузка...
    </div>
  )
}

export default function WaitingPage() {
  return (
    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>Загрузка...</div>}>
      <WaitingContent />
    </Suspense>
  )
}
