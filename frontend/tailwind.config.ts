import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    fontFamily: {
      sans: ["Figtree Variable", "Figtree", ...defaultTheme.fontFamily.sans],
      mono: ["Space Mono", ...defaultTheme.fontFamily.mono],
      display: ["Figtree Variable", "Figtree", ...defaultTheme.fontFamily.sans],
    },
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        // Freya brand cyan (semantic, non-shadcn surfaces).
        brand: {
          DEFAULT: "var(--brand)",
          hover: "var(--brand-hover)",
          foreground: "var(--brand-foreground)",
          subtle: "var(--brand-subtle)",
        },
        // Diarization speakers.
        speaker1: {
          DEFAULT: "var(--speaker-1)",
          subtle: "var(--speaker-1-subtle)",
        },
        speaker2: {
          DEFAULT: "var(--speaker-2)",
          subtle: "var(--speaker-2-subtle)",
        },
        speaker3: {
          DEFAULT: "var(--speaker-3)",
          subtle: "var(--speaker-3-subtle)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        chart: {
          "1": "var(--chart-1)",
          "2": "var(--chart-2)",
          "3": "var(--chart-3)",
          "4": "var(--chart-4)",
          "5": "var(--chart-5)",
        },
        sidebar: {
          DEFAULT: "var(--sidebar)",
          foreground: "var(--sidebar-foreground)",
          primary: "var(--sidebar-primary)",
          "primary-foreground": "var(--sidebar-primary-foreground)",
          accent: "var(--sidebar-accent)",
          "accent-foreground": "var(--sidebar-accent-foreground)",
          border: "var(--sidebar-border)",
          ring: "var(--sidebar-ring)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 4px)",
        "2xl": "calc(var(--radius) + 12px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "none" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        pop: {
          "0%": { transform: "scale(1)" },
          "45%": { transform: "scale(1.05)" },
          "100%": { transform: "scale(1)" },
        },
        "pulse-speaker": {
          "0%": {
            boxShadow: "0 0 0 0 color-mix(in oklch, var(--pulse-color, var(--brand)) 35%, transparent)",
          },
          "70%, 100%": { boxShadow: "0 0 0 8px transparent" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-up": "fade-up 0.55s cubic-bezier(0.16, 1, 0.3, 1) both",
        "fade-in": "fade-in 0.4s ease both",
        pop: "pop 0.32s cubic-bezier(0.16, 1, 0.3, 1)",
        "pulse-speaker": "pulse-speaker 2.4s ease-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
