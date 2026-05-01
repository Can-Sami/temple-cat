import "@testing-library/jest-dom";

if (!globalThis.matchMedia) {
  globalThis.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
      // Legacy API some libs still call.
      addListener: () => {},
      removeListener: () => {},
    }) as unknown as MediaQueryList;
}
