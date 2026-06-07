import { TextInput, MultiSelect, TagsInput, Switch, Select, Button, Stack, Group } from '@mantine/core'
import { useForm } from '@mantine/form'
import { useNavigate } from 'react-router-dom'
import type { SearchFormValues } from '../types/api'

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

  const form = useForm<SearchFormValues>({
    initialValues: {
      word: '',
      variants: false,
      section_type: [],
      primary_writer: [],
      co_writer: [],
      page_size: '20',
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

        <MultiSelect
          label="Primary writer"
          placeholder="All writers"
          data={PRIMARY_WRITER_OPTIONS}
          clearable
          {...form.getInputProps('primary_writer')}
        />

        <MultiSelect
          label="Section type"
          placeholder="All section types"
          data={SECTION_TYPE_OPTIONS}
          clearable
          {...form.getInputProps('section_type')}
        />

        <TagsInput
          label="Co-writer"
          description="Press Enter after each name"
          placeholder="e.g. Jack Antonoff"
          splitChars={[',']}
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
