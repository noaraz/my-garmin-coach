import { useState, useEffect } from 'react'
import type { Profile, ProfileUpdate } from '../api/types'
import { fetchProfile, updateProfile } from '../api/client'

export function useProfile() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const save = async (data: ProfileUpdate) => {
    const updated = await updateProfile(data)
    setProfile(updated)
  }

  return { profile, loading, error, save }
}
