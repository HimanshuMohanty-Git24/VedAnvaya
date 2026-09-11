import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";
import React from "react";

// next/link needs the app router context, which jsdom component tests do not have.
vi.mock("next/link", () => ({
    default: ({
        href,
        children,
        ...rest
    }: {
        href: string;
        children: React.ReactNode;
    } & Record<string, unknown>) => React.createElement("a", { href, ...rest }, children),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
    usePathname: () => "/",
    useSearchParams: () => new URLSearchParams(),
    notFound: () => {
        throw new Error("notFound");
    },
}));

vi.mock("next-themes", () => ({
    useTheme: () => ({ resolvedTheme: "light", setTheme: vi.fn() }),
    ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

if (!window.matchMedia) {
    Object.defineProperty(window, "matchMedia", {
        writable: true,
        value: (query: string) => ({
            matches: false,
            media: query,
            addEventListener: () => {},
            removeEventListener: () => {},
            addListener: () => {},
            removeListener: () => {},
            dispatchEvent: () => false,
        }),
    });
}

if (!window.ResizeObserver) {
    window.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    };
}
