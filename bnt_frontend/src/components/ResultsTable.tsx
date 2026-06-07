import { DataTable } from 'mantine-datatable'
import { Badge, Stack, Text, Group } from '@mantine/core'
import type { SongResult, SearchMeta } from '../types/api'

interface ResultsTableProps {
  results: SongResult[]
  meta: SearchMeta
  onPageChange: (page: number) => void
}

// Displayed inside an expanded row — shows each matching section and its lines.
function SongDetail({ song }: { song: SongResult }) {
  return (
    <Stack gap="sm" p="md" pl="xl">
      {song.sections.map((section) => (
        <div key={section.id}>
          <Group gap="xs" mb={4}>
            <Badge size="sm" variant="light">
              {section.type}
            </Badge>
          </Group>
          <Stack gap={2}>
            {section.lines.map((line) => (
              <Text key={line.id} size="sm" c="dimmed" fs="italic">
                {line.lyric}
              </Text>
            ))}
          </Stack>
        </div>
      ))}
    </Stack>
  )
}

// Attach computed counts to each row so DataTable can use them as accessors.
type TableRecord = SongResult & { sectionCount: number; lineCount: number }

function toTableRecords(results: SongResult[]): TableRecord[] {
  return results.map((song) => ({
    ...song,
    sectionCount: song.sections.length,
    lineCount: song.sections.reduce((acc, s) => acc + s.lines.length, 0),
  }))
}

export default function ResultsTable({ results, meta, onPageChange }: ResultsTableProps) {
  const records = toTableRecords(results)

  return (
    <DataTable<TableRecord>
      withTableBorder
      withColumnBorders
      striped
      highlightOnHover
      idAccessor="id"
      columns={[
        {
          accessor: 'title',
          title: 'Song',
          render: (record) => (
            <div>
              <Text fw={500}>{record.title}</Text>
              <Text size="xs" c="dimmed">
                {record.artist}
              </Text>
            </div>
          ),
        },
        {
          accessor: 'writers',
          title: 'Writers',
          render: (record) => (
            <Text size="sm">{record.writers.map((w) => w.name).join(', ')}</Text>
          ),
        },
        {
          accessor: 'sectionCount',
          title: 'Sections',
          width: 90,
          textAlign: 'center',
        },
        {
          accessor: 'lineCount',
          title: 'Lines',
          width: 70,
          textAlign: 'center',
        },
      ]}
      records={records}
      totalRecords={meta.total_songs}
      recordsPerPage={meta.page_size}
      page={meta.page}
      onPageChange={onPageChange}
      noRecordsText="No results found."
      rowExpansion={{
        content: ({ record }) => <SongDetail song={record} />,
      }}
    />
  )
}
