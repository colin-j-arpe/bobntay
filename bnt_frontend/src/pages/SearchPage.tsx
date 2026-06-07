import { Container, Title, Paper } from '@mantine/core'
import SearchForm from '../components/SearchForm'

export default function SearchPage() {
  return (
    <Container size="sm" py="xl">
      <Title order={1} mb="lg">
        Lyric Search
      </Title>
      <Paper withBorder p="lg" radius="md">
        <SearchForm />
      </Paper>
    </Container>
  )
}
