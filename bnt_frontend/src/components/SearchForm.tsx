import { useMemo, useState } from 'react'
import { TextInput, Checkbox, MultiSelect, Switch, Select, Button, Stack, Group } from '@mantine/core'
import { useForm } from '@mantine/form'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useWriters } from '../api/writers'
import type { SearchFormValues } from '../types/api'

function fuzzyFilter(name: string, query: string): boolean {
  const lower = name.toLowerCase()
  return [...query.toLowerCase()].every((ch) => lower.includes(ch))
}

const SECTION_TYPE_OPTIONS = [
  { value: 'INTRO', label: 'Intro' },
  { value: 'VERSE', label: 'Verse' },
  { value: 'PRECHORUS', label: 'Pre-Chorus' },
  { value: 'CHORUS', label: 'Chorus' },
  { value: 'POSTCHORUS', label: 'Post-Chorus' },
  { value: 'BRIDGE', label: 'Bridge' },
  { value: 'BREAKDOWN', label: 'Breakdown' },
  { value: 'SPOKEN', label: 'Spoken' },
  { value: 'CODA', label: 'Coda' },
  { value: 'OUTRO', label: 'Outro' },
  { value: 'OTHER', label: 'Other' },
]

const PRIMARY_WRITER_OPTIONS = [
  { value: 'Robert Pollard', label: 'Robert Pollard' },
  { value: 'Taylor Swift', label: 'Taylor Swift' },
]

const PAGE_SIZE_OPTIONS = ['10', '20', '50']

export default function SearchForm() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { data: writers, isLoading: isLoadingWriters } = useWriters()
  const [writerSearch, setWriterSearch] = useState('')

  const filteredWriters = useMemo(() => {
    if (!writers) return []
    if (!writerSearch) return writers
    return writers.filter((name) => fuzzyFilter(name, writerSearch))
  }, [writers, writerSearch])

  // Seed from URL when returning from results; default primary_writer to all on fresh visit.
  const hasWord = searchParams.has('word')
  const form = useForm<SearchFormValues>({
    initialValues: {
      word: searchParams.get('word') ?? '',
      variants: searchParams.get('variants') === 'true',
      section_type: searchParams.getAll('section_type'),
      primary_writer: hasWord
        ? searchParams.getAll('primary_writer')
        : PRIMARY_WRITER_OPTIONS.map((o) => o.value),
      co_writer: searchParams.getAll('co_writer'),
      page_size: searchParams.get('page_size') ?? '20',
    },
    validate: {
      word: (v) => (v.trim() ? null : 'Search term is required'),
    },
  })

  const handleSubmit = (values: SearchFormValues) => {
    const params = new URLSearchParams()
    params.set('word', values.word.trim())
    if (values.variants) params.set('variants', 'true')
    values.section_type.forEach((t) => params.append('section_type', t))
    values.primary_writer.forEach((w) => params.append('primary_writer', w))
    values.co_writer.forEach((w) => params.append('co_writer', w))
    params.set('page_size', values.page_size)
    navigate(`/results?${params.toString()}`)
  }

  return (
    <form noValidate onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        <TextInput
          label="Search word"
          placeholder="Enter a word..."
          required
          {...form.getInputProps('word')}
        />

        <Checkbox.Group label="Primary writer" {...form.getInputProps('primary_writer')}>
          <Stack gap="xs" mt="xs">
            {PRIMARY_WRITER_OPTIONS.map((opt) => (
              <Checkbox key={opt.value} value={opt.value} label={opt.label} />
            ))}
          </Stack>
        </Checkbox.Group>

        <MultiSelect
          label="Section type"
          placeholder="All section types"
          data={SECTION_TYPE_OPTIONS}
          clearable
          {...form.getInputProps('section_type')}
        />

        <MultiSelect
          label="Co-writer"
          placeholder={isLoadingWriters ? 'Loading…' : 'Search writers…'}
          data={filteredWriters}
          searchable
          searchValue={writerSearch}
          onSearchChange={setWriterSearch}
          clearable
          disabled={isLoadingWriters}
          {...form.getInputProps('co_writer')}
        />

        <Switch
          label="Include word variants (plurals, conjugations, etc.)"
          {...form.getInputProps('variants', { type: 'checkbox' })}
        />

        <Select
          label="Results per page"
          data={PAGE_SIZE_OPTIONS}
          {...form.getInputProps('page_size')}
        />

        <Group>
          <Button type="submit">Search</Button>
        </Group>
      </Stack>
    </form>
  )
}
