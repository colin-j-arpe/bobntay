import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import { describe, it, expect, vi } from 'vitest'
import SearchForm from '../components/SearchForm'

vi.mock('../api/writers', () => ({
  useWriters: () => ({ data: ['Annie Clark', 'Jack Antonoff', 'St. Vincent'], isLoading: false }),
}))

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <MemoryRouter initialEntries={['/']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <MantineProvider>{children}</MantineProvider>
    </MemoryRouter>
  )
}

// Captures the search string after navigation to /results.
function LocationCapture({ onCapture }: { onCapture: (search: string) => void }) {
  const location = useLocation()
  onCapture(location.search)
  return null
}

function renderWithRouter(onNavigate: (search: string) => void) {
  return render(
    <MemoryRouter initialEntries={['/']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <MantineProvider>
        <Routes>
          <Route path="/" element={<SearchForm />} />
          <Route path="/results" element={<LocationCapture onCapture={onNavigate} />} />
        </Routes>
      </MantineProvider>
    </MemoryRouter>,
  )
}

describe('SearchForm', () => {
  it('renders the word input', () => {
    render(<SearchForm />, { wrapper: Wrapper })
    expect(screen.getByRole('textbox', { name: /search word/i })).toBeInTheDocument()
  })

  it('renders the primary writer selector', () => {
    render(<SearchForm />, { wrapper: Wrapper })
    expect(screen.getByText(/primary writer/i)).toBeInTheDocument()
  })

  it('renders the section type selector', () => {
    render(<SearchForm />, { wrapper: Wrapper })
    expect(screen.getByText(/section type/i)).toBeInTheDocument()
  })

  it('renders the co-writer selector', () => {
    render(<SearchForm />, { wrapper: Wrapper })
    expect(screen.getByText(/co-writer/i)).toBeInTheDocument()
  })

  it('includes co_writer in the URL when a writer is selected', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    renderWithRouter(onNavigate)

    await user.type(screen.getByRole('textbox', { name: /search word/i }), 'love')

    const coWriterInput = screen.getByRole('textbox', { name: /co-writer/i })
    await user.click(coWriterInput)
    await user.click(screen.getByText('Jack Antonoff'))

    await user.click(screen.getByRole('button', { name: /search/i }))

    await waitFor(() => expect(onNavigate).toHaveBeenCalled())
    expect(onNavigate.mock.calls[0][0]).toContain('co_writer=Jack+Antonoff')
  })

  it('renders the variants toggle', () => {
    render(<SearchForm />, { wrapper: Wrapper })
    // Mantine Switch renders with role="switch", not role="checkbox"
    expect(screen.getByRole('switch', { name: /include word variants/i })).toBeInTheDocument()
  })

  it('shows a validation error when submitted without a word', async () => {
    const user = userEvent.setup()
    render(<SearchForm />, { wrapper: Wrapper })

    await user.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByText(/search term is required/i)).toBeInTheDocument()
  })

  it('navigates to /results with the word param on submit', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    renderWithRouter(onNavigate)

    await user.type(screen.getByRole('textbox', { name: /search word/i }), 'love')
    await user.click(screen.getByRole('button', { name: /search/i }))

    await waitFor(() => expect(onNavigate).toHaveBeenCalled())
    expect(onNavigate.mock.calls[0][0]).toContain('word=love')
  })

  it('includes variants=true in the URL when the toggle is on', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    renderWithRouter(onNavigate)

    await user.type(screen.getByRole('textbox', { name: /search word/i }), 'run')
    await user.click(screen.getByRole('switch', { name: /include word variants/i }))
    await user.click(screen.getByRole('button', { name: /search/i }))

    await waitFor(() => expect(onNavigate).toHaveBeenCalled())
    expect(onNavigate.mock.calls[0][0]).toContain('variants=true')
  })
})
