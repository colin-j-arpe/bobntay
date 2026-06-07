import { useQuery } from '@tanstack/react-query'
import type { SearchParams, SearchResponse } from '../types/api'

export function buildSearchUrl(params: SearchParams): string {
  const urlParams = new URLSearchParams()
  urlParams.set('word', params.word)
  if (params.variants) urlParams.set('variants', 'true')
  params.section_type?.forEach((t) => urlParams.append('section_type', t))
  params.primary_writer?.forEach((w) => urlParams.append('primary_writer', w))
  params.co_writer?.forEach((w) => urlParams.append('co_writer', w))
  if (params.page != null) urlParams.set('page', String(params.page))
  if (params.page_size != null) urlParams.set('page_size', String(params.page_size))
  return `/search/word/?${urlParams.toString()}`
}

export async function fetchWordSearch(params: SearchParams): Promise<SearchResponse> {
  const response = await fetch(buildSearchUrl(params))
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `Request failed: ${response.status}`)
  }
  return response.json() as Promise<SearchResponse>
}

export function useWordSearch(params: SearchParams | null) {
  return useQuery({
    queryKey: ['wordSearch', params],
    queryFn: () => fetchWordSearch(params!),
    enabled: params !== null && params.word.trim() !== '',
    staleTime: 5 * 60 * 1000,
  })
}
