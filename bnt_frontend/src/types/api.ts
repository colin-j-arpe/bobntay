export interface SearchFormValues {
  word: string
  variants: boolean
  section_type: string[]
  primary_writer: string[]
  co_writer: string[]
  page_size: string
}

export interface WordData {
  id: number | null
  text: string
}

export interface LineResult {
  id: number
  order: number
  lyric: string
}

export interface SectionResult {
  id: number
  type: string
  order: number
  lines: LineResult[]
}

export interface WriterResult {
  id: number
  name: string
}

export interface SongResult {
  id: number
  title: string
  artist: string
  writers: WriterResult[]
  sections: SectionResult[]
}

export interface SearchMeta {
  total_songs: number
  total_lines: number
  writers_in_results: string[]
  page: number
  page_size: number
  previous_page_url: string | null
  next_page_url: string | null
}

export interface SearchResponse {
  data: {
    word: WordData
    results: SongResult[]
  }
  meta: SearchMeta
}

export interface SearchParams {
  word: string
  variants?: boolean
  section_type?: string[]
  primary_writer?: string[]
  co_writer?: string[]
  page?: number
  page_size?: number
}
