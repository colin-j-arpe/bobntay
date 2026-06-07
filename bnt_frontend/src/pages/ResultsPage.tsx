import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Title,
  Text,
  Button,
  Group,
  Stack,
  Alert,
  Loader,
  Center,
} from '@mantine/core'
import { useWordSearch } from '../api/wordSearch'
import ResultsTable from '../components/ResultsTable'
import type { SearchParams } from '../types/api'

function parseSearchParams(urlParams: URLSearchParams): SearchParams {
  return {
    word: urlParams.get('word') ?? '',
    variants: urlParams.get('variants') === 'true',
    section_type: urlParams.getAll('section_type'),
    primary_writer: urlParams.getAll('primary_writer'),
    co_writer: urlParams.getAll('co_writer'),
    page: Number(urlParams.get('page') ?? '1'),
    page_size: Number(urlParams.get('page_size') ?? '20'),
  }
}

export default function ResultsPage() {
  const [urlParams, setUrlParams] = useSearchParams()
  const navigate = useNavigate()
  const searchParams = parseSearchParams(urlParams)

  const { data, isLoading, isError, error } = useWordSearch(
    searchParams.word ? searchParams : null,
  )

  const handlePageChange = (page: number) => {
    const next = new URLSearchParams(urlParams)
    next.set('page', String(page))
    setUrlParams(next, { replace: true })
  }

  if (!searchParams.word) {
    return (
      <Container py="xl">
        <Text>No search term provided.</Text>
        <Button mt="md" onClick={() => navigate('/')}>
          Back to search
        </Button>
      </Container>
    )
  }

  return (
    <Container size="lg" py="xl">
      <Group mb="lg" align="baseline">
        <Button variant="subtle" onClick={() => navigate(-1)}>
          ← Back
        </Button>
        <Title order={2}>
          Results for &ldquo;{data?.data.word.text ?? searchParams.word}&rdquo;
        </Title>
      </Group>

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" title="Error">
          {(error as Error).message}
        </Alert>
      )}

      {data && (
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            {data.meta.total_songs} song{data.meta.total_songs !== 1 ? 's' : ''},{' '}
            {data.meta.total_lines} matching line{data.meta.total_lines !== 1 ? 's' : ''}
          </Text>
          <ResultsTable
            results={data.data.results}
            meta={data.meta}
            onPageChange={handlePageChange}
          />
        </Stack>
      )}
    </Container>
  )
}
