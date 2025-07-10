import type { Config } from "tailwindcss";
import animatePlugin from "tailwindcss-animate";

const config: Config = {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: "selector",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
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
        "search-move": {
          from: { transform: "translateY(0)" },
          to: { transform: "translateY(-50vh)" },
        },
        "logo-scale": {
          from: { transform: "scale(1)" },
          to: { transform: "scale(0.8)" },
        },
        "pulse-to-light": {
          "0%": { transform: "scale(1)", opacity: "0.5" },
          "10%": { transform: "scale(1)" },
          "75%": { opacity: "1" },
          "100%": { opacity: "0", transform: "scale(1)" },
        },
        "pulse-to-dark": {
          "0%": { transform: "scale(0)", opacity: "0.5" },
          "10%": { transform: "scale(1)" },
          "75%": { opacity: "1" },
          "100%": { opacity: "0", transform: "scale(1)" },
        },
        "goo-open": {
          "0%": { transform: "translateY(-10%) scaleY(0.3)" },
          "100%": { transform: "translateY(0) scaleY(1)" },
        },
        "goo-close": {
          "0%": { transform: "translateY(0) scaleY(1)" },
          "100%": { transform: "translateY(-10%) scaleY(0.3)" },
        },
        "goo-parent-ripple": {
          "0%": { borderBottomLeftRadius: "var(--radius)", borderBottomRightRadius: "var(--radius)" },
          "50%": { borderBottomLeftRadius: "50%", borderBottomRightRadius: "50%" },
          "100%": { borderBottomLeftRadius: "var(--radius)", borderBottomRightRadius: "var(--radius)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "search-move": "search-move 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "logo-scale": "logo-scale 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "pulse-to-light": "pulse-to-light 650ms ease-out",
        "pulse-to-dark": "pulse-to-dark 650ms ease-out",
        "goo-open": "goo-open 0.45s cubic-bezier(0.22, 1, 0.36, 1)",
        "goo-close": "goo-close 0.3s cubic-bezier(0.55, 0, 0.6, 0.18)",
        "goo-parent-ripple": "goo-parent-ripple 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
    },
  },
  plugins: [animatePlugin],
};

export default config;