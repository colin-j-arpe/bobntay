import { render, screen } from '@testing-library/react'
import { MantineProvider } from '@mantine/core'
import { describe, it, expect, vi } from 'vitest'
import ResultsTable from '../components/ResultsTable'
import type { SongResult, SearchMeta } from '../types/api'

// Mock mantine-datatable so tests don't depend on its layout-engine internals
// (it defers column rendering until it can measure the scroll container).
// The mock renders columns and records using the same render functions we pass,
// so we still test ResultsTable's data-shaping logic.
vi.mock('mantine-datatable', () => ({
  DataTable: ({
    records = [],
    columns = [],
    noRecordsText,
  }: {
    records: Record<string, unknown>[]
    columns: {
      accessor: string
      render?: (record: Record<string, unknown>) => React.ReactNode
    }[]
    noRecordsText?: string
  }) =>
    records.length === 0 ? (
      <div>{noRecordsText}</div>
    ) : (
      <table>
        <tbody>
          {records.map((record) => (
            <tr key={String(record.id)}>
              {columns.map((col) => (
                <td key={col.accessor}>
                  {col.render
                    ? col.render(record)
                    : String((record[col.accessor] as string | number | boolean | null | undefined) ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    ),
}))

// Reflects the API response shape for a search on "scientist" against
// "I Am a Scientist" by Guided by Voices — only lines containing the
// search word are returned, grouped by the section they appear in.
const MOCK_RESULTS: SongResult[] = [
  {
    id: 1,
    title: 'I Am a Scientist',
    artist: 'Guided by Voices',
    writers: [{ id: 1, name: 'Robert Pollard' }],
    sections: [
      {
        id: 10,
        type: 'VERSE',
        order: 1,
        lines: [
          { id: 100, order: 1, lyric: 'I am a scientist, I seek to understand me' },
          { id: 101, order: 2, lyric: 'All of my impurities and evils yet unknown' },
        ],
      },
      {
        id: 11,
        type: 'OUTRO',
        order: 5,
        lines: [
          { id: 101, order: 1, lyric: 'I am a scientist, I seek to understand me' },
        ],
      },
    ],
  },
]

const BASE_META: SearchMeta = {
  total_songs: 1,
  total_lines: 3,
  writers_in_results: ['Robert Pollard'],
  page: 1,
  page_size: 20,
  previous_page_url: null,
  next_page_url: null,
}

function renderTable(results = MOCK_RESULTS, meta = BASE_META) {
  return render(
    <MantineProvider>
      <ResultsTable results={results} meta={meta} onPageChange={vi.fn()} />
    </MantineProvider>,
  )
}

describe('ResultsTable', () => {
  it('renders the song title', () => {
    renderTable()
    expect(screen.getByText('I Am a Scientist')).toBeInTheDocument()
  })

  it('renders the artist name', () => {
    renderTable()
    expect(screen.getByText('Guided by Voices')).toBeInTheDocument()
  })

  it('renders the writer name', () => {
    renderTable()
    expect(screen.getByText('Robert Pollard')).toBeInTheDocument()
  })

  it('renders the correct section count', () => {
    renderTable()
    // The mock song has 2 sections (VERSE and OUTRO)
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders the correct line count', () => {
    renderTable()
    // VERSE has 2 lines, OUTRO has 1 line = 3 total
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows no-records text when results are empty', () => {
    renderTable([], { ...BASE_META, total_songs: 0, total_lines: 0, writers_in_results: [] })
    expect(screen.getByText(/no results found/i)).toBeInTheDocument()
  })

  it('renders multiple songs', () => {
    const twoSongs: SongResult[] = [
      ...MOCK_RESULTS,
      {
        id: 2,
        title: 'Echos Myron',
        artist: 'Guided by Voices',
        writers: [{ id: 1, name: 'Robert Pollard' }],
        sections: [
          {
            id: 20,
            type: 'VERSE',
            order: 1,
            lines: [{ id: 200, order: 1, lyric: 'Scientist or mathematician' }],
          },
        ],
      },
    ]
    renderTable(twoSongs, { ...BASE_META, total_songs: 2, total_lines: 3 })
    expect(screen.getByText('I Am a Scientist')).toBeInTheDocument()
    expect(screen.getByText('Echos Myron')).toBeInTheDocument()
  })
})
