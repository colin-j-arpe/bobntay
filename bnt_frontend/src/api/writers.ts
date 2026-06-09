import { useQuery } from '@tanstack/react-query'

async function fetchWriters(): Promise<string[]> {
  const response = await fetch('/search/writers/')
  if (!response.ok) throw new Error(`Failed to fetch writers: ${response.status}`)
  const data = await response.json() as { writers: string[] }
  return data.writers
}

export function useWriters() {
  return useQuery({
    queryKey: ['writers'],
    queryFn: fetchWriters,
    staleTime: 60 * 60 * 1000,
  })
}
