"use client";

import { Moon, Sun } from "@phosphor-icons/react";
import { useTheme } from "next-themes";

/**
 * Both icons render on the server and the client; CSS picks the visible one from
 * the theme class on <html>. That keeps the first paint stable without a
 * mounted-flag round trip.
 */
export function ThemeToggle() {
    const { resolvedTheme, setTheme } = useTheme();
    return (
        <button
            className="icon-button theme-toggle"
            type="button"
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            aria-label="Switch between light and dark theme"
        >
            <Moon size={18} className="theme-icon-light" aria-hidden="true" />
            <Sun size={18} className="theme-icon-dark" aria-hidden="true" />
        </button>
    );
}
