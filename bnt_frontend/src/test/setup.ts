import '@testing-library/jest-dom'

// jsdom does not implement ResizeObserver or window.matchMedia.
// Both are required by Mantine components and mantine-datatable.
//
// ResizeObserver must fire its callback immediately in observe() with non-zero
// dimensions so that mantine-datatable renders column cells (it withholds
// rendering until it knows the container width).
class ImmediateResizeObserver {
  private callback: ResizeObserverCallback

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback
  }

  observe(target: Element): void {
    this.callback(
      [
        {
          target,
          contentRect: {
            width: 1280, height: 800,
            top: 0, left: 0, bottom: 800, right: 1280, x: 0, y: 0,
            toJSON: () => ({}),
          } as DOMRectReadOnly,
          borderBoxSize:              [{ blockSize: 800, inlineSize: 1280 }] as ReadonlyArray<ResizeObserverSize>,
          contentBoxSize:             [{ blockSize: 800, inlineSize: 1280 }] as ReadonlyArray<ResizeObserverSize>,
          devicePixelContentBoxSize:  [{ blockSize: 800, inlineSize: 1280 }] as ReadonlyArray<ResizeObserverSize>,
        } as ResizeObserverEntry,
      ],
      this as unknown as ResizeObserver,
    )
  }

  unobserve(): void {}
  disconnect(): void {}
}

global.ResizeObserver = ImmediateResizeObserver as unknown as typeof ResizeObserver

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})
